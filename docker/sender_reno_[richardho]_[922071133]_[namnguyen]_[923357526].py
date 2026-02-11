import socket
from datetime import datetime
import subprocess
import os
import time
import signal
from enum import Enum

# total packet size
PACKET_SIZE = 1024
# bytes reserved for sequence id
SEQ_NUM_SIZE = 4
# bytes available for message
MESSAGE_SIZE = PACKET_SIZE - SEQ_NUM_SIZE

class STATE(Enum):
    slow_start = 0
    congestion_avoidance = 1
    fast_retransmit = 2
    fast_recovery = 3
    
 
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

        # initialize congestion window and threshold
        cwnd = 1
        ssthresh = 64
        state = STATE.slow_start

        # index of the earliest unacked pkt 
        head = 0
        # index of the next packet that can be sent 
        tail = 0
        # byte offset
        seq_num_head = 0
        seq_num_tail = 0

        last_ack = 0
        ack_dups = 0

        # used to estimate RTT in congestion avoidance
        ca_acked = 0
        
        while seq_num_head < len(data):
            # send next packets in the window range
            while seq_num_tail < len(data) and tail < head + cwnd:
                pkt = make_packet(data, seq_num_tail)
                udp_socket.sendto(pkt, receiver)
                if seq_num_tail not in first_time_sent:
                    first_time_sent[seq_num_tail] = datetime.now()
                tail += 1
                seq_num_tail += payload_size(data, seq_num_tail)

            try:
                # receive ack from the receiver
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack_time = datetime.now()
                ack_num = int.from_bytes(ack[:SEQ_NUM_SIZE], byteorder="big", signed=True)
                print(ack_num, ack[SEQ_NUM_SIZE:])

                # duplicate acks
                if last_ack == ack_num:
                    if state == STATE.slow_start or state == STATE.congestion_avoidance:
                        ack_dups += 1
                        #Fast retransmit
                        if ack_dups == 3:
                            pkt = make_packet(data, ack_num)
                            udp_socket.sendto(pkt, receiver)
                            state = STATE.fast_recovery
                            ack_dups = 0
                            ssthresh = max(cwnd // 2, 1)
                            cwnd = ssthresh + 3
                    elif state == STATE.fast_recovery:
                        cwnd += 1 #increment cwnd for each dup ACK

                # receive new ACKs
                elif ack_num > last_ack:
                    last_ack = ack_num
                    ack_dups = 0
                    #If currently in fast recovery, enter congestion avoidance
                    if state == STATE.fast_recovery:
                        cwnd = ssthresh
                        state = STATE.congestion_avoidance
                        ca_acked = 0
                    
                    count = 0 #keep track the number of new-acked packets
                    while True:
                        ps = payload_size(data, seq_num_head)
                        if ps != 0 and seq_num_head + ps <= ack_num:
                            delays.append((ack_time - first_time_sent[seq_num_head]).total_seconds())
                            first_time_sent.pop(seq_num_head)
                            head += 1
                            seq_num_head += ps
                            count += 1
                        else:
                            # increment cwnd by 1 for each ACK
                            if state == STATE.slow_start:
                                cwnd += count
                            elif state == STATE.congestion_avoidance:
                                ca_acked += count
                                if ca_acked >= cwnd:
                                    # increment cwnd by 1 for each RTT
                                    cwnd += 1
                                    ca_acked -= cwnd

                            break
                    
                    if state == STATE.slow_start and cwnd >= ssthresh:
                        # Enter congestion avoidance state
                        state = STATE.congestion_avoidance
                        ca_acked = 0
            
            except socket.timeout:
                #Enter the slow start again
                ssthresh = max(cwnd // 2, 1)
                cwnd = 1
                state = STATE.slow_start
                tail = head
                seq_num_tail = seq_num_head
                ca_acked = 0
                #Resend the oldest acked packet
                pkt = make_packet(data, seq_num_head)
                udp_socket.sendto(pkt, receiver)


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

    print(f"Throughput: {throughput:.7f}")
    print(f"Average per-packet delay: {adpp:.7f}")
    print(f"Performance: {performance:.7f}")
    