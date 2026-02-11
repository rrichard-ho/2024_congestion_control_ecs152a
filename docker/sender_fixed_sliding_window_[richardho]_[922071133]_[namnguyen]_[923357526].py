import socket
from datetime import datetime
import subprocess
import os
import time
import signal

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_NUM_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_NUM_SIZE
# total packets to send
WINDOW_SIZE = 1


def make_packet(data, seq_num):
    return int.to_bytes(seq_num, SEQ_NUM_SIZE, byteorder="big", signed=True) + data[seq_num : seq_num + MESSAGE_SIZE]

def payload_size(data, seg_num):
    return len(data[seg_num : seg_num + MESSAGE_SIZE])


def sender(data):

    first_time_sent = {}
    delays = []
    throughput = None

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        udp_socket.bind(("0.0.0.0", 5000))
        udp_socket.settimeout(1)
        start_t = datetime.now()

        receiver = ("localhost", 5001)

        # index of the earliest unacked pkt 
        head = 0
        # index of the next packet that can be sent 
        tail = 0
        # byte offset
        seq_num_head = 0
        seq_num_tail = 0

        while seq_num_head < len(data):
            # send next packets in the window range
            while seq_num_tail < len(data) and tail < head + WINDOW_SIZE:
                pkt = make_packet(data, seq_num_tail)
                udp_socket.sendto(pkt, receiver)
                if seq_num_tail not in first_time_sent:
                    first_time_sent[seq_num_tail] = datetime.now()
                tail += 1
                seq_num_tail += payload_size(data, seq_num_tail)

            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack_time = datetime.now()
                ack_num = int.from_bytes(ack[:SEQ_NUM_SIZE], byteorder="big", signed=True)
                print(ack_num, ack[SEQ_NUM_SIZE:])

                # keep track accumalative ACKs
                while True:
                    ps = payload_size(data, seq_num_head)
                    if ps != 0 and seq_num_head + ps <= ack_num:
                        delays.append((ack_time - first_time_sent[seq_num_head]).total_seconds())
                        first_time_sent.pop(seq_num_head)
                        head += 1
                        seq_num_head += ps
                    else:
                        break
            
            except socket.timeout:
                seq_num_tmp = seq_num_head
                # go-back-N
                for _ in range(head, tail):
                    pkt = make_packet(data, seq_num_tmp)
                    udp_socket.sendto(pkt, receiver)
                    seq_num_tmp += payload_size(data, seq_num_tmp)

        # send fin packet 
        fin_packet = int.to_bytes(
            len(data), SEQ_NUM_SIZE, byteorder="big", signed=True
        ) + b'==FINACK=='
        udp_socket.sendto(fin_packet, receiver)

        throughput = len(data) / (datetime.now() - start_t).total_seconds()
        adpp = sum(delays) / len(delays)
        performance = 0.3*throughput/1000 + 0.7/adpp
    
        return throughput, adpp, performance
    
if __name__=="__main__":
    N = 10
    data = None 
    throughputs = []
    adpps = []
    performances = []
    # read data from .mp3 file
    with open("file.mp3", "rb") as f:
        data = f.read()
    for _ in range(N):
        proc = subprocess.Popen(
            ["bash", "./start-simulator.sh"],
            start_new_session=True,  
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(2)

        t, a, p = sender(data=data)
        throughputs.append(t)
        adpps.append(a)
        performances.append(p)

        os.killpg(proc.pid, signal.SIGTERM)
    
    throughput = sum(throughputs) / len(throughputs)
    adpp = sum(adpps) / len(adpps)
    performance = sum(performances) / len(performances)

    print(f"Throughput: {throughput:.7f} bytes/second")
    print(f"Average per-packet delay: {adpp:.7f} seconds")
    print(f"Performance: {performance:.7f}")