import socket
from datetime import datetime

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE


# puts a seq_id in front of a payload
def make_packet(seq_id, payload):
    return int.to_bytes(seq_id, SEQ_ID_SIZE, byteorder='big', signed=True) + payload

def sender(data):    
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
            PACKET_DELAY_START = datetime.now()
            
            # send packet
            while True:
                udp_socket.sendto(packet, receiver)
                try:
                    while True:
                        ack, _ = udp_socket.recvfrom(PACKET_SIZE)
                        ack_id = int.from_bytes(ack[:SEQ_ID_SIZE], byteorder="big", signed=True)

                        if ack_id == seq_id + MESSAGE_SIZE or ack_id == len(data): # check ack
                            seq_id = ack_id
                            PACKET_DELAY_END = datetime.now()
                            PACKET_DELAY_DELTA = (PACKET_DELAY_END - PACKET_DELAY_START).total_seconds()
                            packet_delay_arr.append(PACKET_DELAY_DELTA)
                            break
                    
                except socket.timeout: # resend if timeout expires
                    continue
                break # send next packet
        
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
                if ack_id >= len(data):
                    break
            except socket.timeout:
                continue
        

        # calculate metrics
        throughput_end = datetime.now()
        throughput_delta = (throughput_end - throughput_start).total_seconds()
        throughput = len(data) / throughput_delta

        cur_avg_packet_delay = sum(packet_delay_arr) / len(packet_delay_arr)

        performance = ((0.3 * throughput) / 1000) + (0.7 / cur_avg_packet_delay)
        
        return throughput, cur_avg_packet_delay, performance
    
if __name__=="__main__":
    data = None
    throughputs = []
    avg_packet_delays = []
    performances = []

    # read data
    with open('file.mp3', 'rb') as f:
        data = f.read()

    throughput, packet_delay, performance = sender(data=data)
    
    print(f"Throughput: {throughput:.7f} bytes/second")
    print(f"Average Per-Packet Delay: {packet_delay:.7f} seconds")
    print(f"Performance {performance:.7f}")
    