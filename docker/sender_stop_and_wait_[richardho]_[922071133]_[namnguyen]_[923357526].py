import socket
from datetime import datetime

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE


# puts a seq_id in front of a payload
def make_packet(seq_id, payload):
    return int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + payload

def receiver(data):    
    packet_delay_arr = []

    # create a udp socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
        
        # bind to a port
        udp_socket.bind(("0.0.0.0", 5000))
        udp_socket.settimeout(1)
        receiver = ('localhost', 5001)
        throughput_start = datetime.now()
        
        seq_id = 0
        # start sending data
        while seq_id < len(data):
            
            # make packet
            print(f"creating {seq_id} to {seq_id + MESSAGE_SIZE}")
            data_chunk = data[seq_id : seq_id + MESSAGE_SIZE]
            packet = make_packet(seq_id, data_chunk)
            PACKET_DELAY_START = datetime.now()
            
            # send packet
            while True:
                # print(f"sending {seq_id} to {seq_id + MESSAGE_SIZE}")
                udp_socket.sendto(packet, receiver)
                try:
                    while True:
                        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                        ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big", signed=True)
                        print(f"ACK: {ack_id} SEQ_ID: {seq_id} End of Payload: {seq_id + MESSAGE_SIZE}")

                        if ack_id == seq_id + MESSAGE_SIZE: # check ack
                            seq_id = ack_id
                            PACKET_DELAY_END = datetime.now()
                            PACKET_DELAY_DELTA = (PACKET_DELAY_END - PACKET_DELAY_START).total_seconds()
                            packet_delay_arr.append(PACKET_DELAY_DELTA)
                            break
                    
                except socket.timeout: # resend if timeout expires
                    print(f"resending {seq_id} to {seq_id + MESSAGE_SIZE}")
                    continue
                break # send next packet
        
        # make fin 
        fin_packet = make_packet(seq_id, b'')
        print("creating fin")

        # send fin
        while True:
            print("sending fin")
            udp_socket.sendto(fin_packet, receiver)
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack_id = int.from_bytes(
                    ack[:SEQ_ID_SIZE], signed=True, byteorder='big'
                )
                if ack_id >= len(data):
                    break
            except socket.timeout:
                print("resending fin")
                continue

        throughput_end = datetime.now()
        throughput_delta = (throughput_end - throughput_start).total_seconds()
        throughput = len(data) / throughput_delta

        cur_avg_packet_delay = sum(packet_delay_arr) / len(packet_delay_arr)

        performance = ((0.3 * throughput) / 1000) + (0.7 / cur_avg_packet_delay)
        
        return throughput, cur_avg_packet_delay, performance
    
if __name__=="__main__":
    N = 1
    data = None
    throughputs = []
    avg_packet_delays = []
    performances = []

    # read data
    with open('file.mp3', 'rb') as f:
        data = f.read()
    for i in range(N):
        throughput, packet_delay, performance = receiver(data=data)
        throughputs.append(throughput)
        avg_packet_delays.append(packet_delay)
        performances.append(performance)
        print(f"[{i+1}] Throughput: {throughput:.7f}")
        print(f"[{i+1}] Average Packet Delay: {packet_delay:.7f}")
        print(f"[{i+1}] Performance {performance:.7f}")
    
    f_throughput = sum(throughputs) / N
    f_packet_delay = sum(avg_packet_delays) / N
    f_performance = sum(performances) / N
    print(f"Average Throughput: {f_throughput:.7f}")
    print(f"Average Per-Packet Delay: {f_packet_delay:.7f}")
    print(f"Average Performance {f_performance:.7f}")
    