import socket
from datetime import datetime

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

N = 10
throughputs = []
avg_delays = []
performances = []

# puts a seq_id in front of a payload
def make_packet(seq_id, payload):
    return int.to_bytes(seq_id, SEQ_ID_SIZE, signed=True, byteorder='big') + payload

for _ in range(N):
    # read data
    with open('file.mp3', 'rb') as f:
        data = f.read()
    
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
            data_chunk = data[seq_id : seq_id + MESSAGE_SIZE]
            packet = make_packet(seq_id, data_chunk)
            
            # send packet
            while True:
                udp_socket.sendto(packet, receiver)
                PACKET_DELAY_START = datetime.now()
                try:
                    ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                    ack_id = int.from_bytes(
                        ack[:SEQ_ID_SIZE], signed=True, byteorder='big'
                    )

                    if ack_id == seq_id + len(data_chunk): # check if ack matches seq_id
                        seq_id = ack_id 
                        PACKET_DELAY_END = datetime.now()
                        PACKET_DELAY_DELTA = (PACKET_DELAY_END - PACKET_DELAY_START).total_seconds()
                        packet_delay_arr.append(PACKET_DELAY_DELTA)
                        break
                except socket.timeout:
                    continue  # resend if timeout expires

        
        # make fin 
        fin_packet = make_packet(seq_id, b'')

        # send fin
        while True:
            udp_socket.sendto(fin_packet, receiver)
            try:
                ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                ack_id = int.from_bytes(
                    ack[:SEQ_ID_SIZE], signed=True, byteorder='big'
                )
                if ack_id == seq_id:
                    break
            except socket.timeout:
                continue
        throughput_end = datetime.now()
        throughput_delta = (throughput_end - throughput_start).total_seconds()
        throughput = len(data) / throughput_delta
        throughputs.append(throughput)

        cur_avg_packet_delay = sum(packet_delay_arr) / len(packet_delay_arr)
        avg_delays.append(cur_avg_packet_delay)

        performance = ((0.3 * throughput) / 1000) + (0.7 / cur_avg_packet_delay)
        performances.append(performance)

avg_throughput = sum(throughputs) / N
avg_packet_delay = sum(avg_delays) / N
avg_performance = sum(performances) / N

print(f"{avg_throughput:.7f}")
print(f"{avg_packet_delay:.7f}")
print(f"{avg_performance:.7f}")