import socket
from threading import Thread
from io import BytesIO
import struct
from yaml import safe_load
from time import sleep
from datetime import datetime
import traceback
import os

dcfg = '''#Configure
#LocalPort
LocalPort: 25565
#Server IP Address
ServerIpAddress: 'mc.hypixel.net'
#ServerPort
ServerPort: 25565
#Maximum connection
Maxmium: 10
#White List Check
WCheck: false
#Motd Message
MotdMsg: '{\"version\":{\"name\":\"FAMStudio\",\"protocol\":47},\"players\":{\"max\":114514,\"online\":114514,\"sample\":[]},\"description\":{\"text\":\"当前线路AWS美国旧金山\"}}'
#Bypass Hypixel Unoffcial IP Check
BypassIpCheck: false
'''

while True:
    try:
        cfg = safe_load(open('config.yml', 'r', errors='ignore'))
        open('logs/normal.log', 'r')
        open('logs/errorlog.log', 'r')
        open('list.txt', 'r')
        break
    except:
        open('config.yml', 'w').write(dcfg)
        if not os.path.exists('logs'):
            os.mkdir('logs')
        open('logs/normal.log', 'w')
        open('logs/errorlog.log', 'w')
        open('list.txt', 'w')
        sleep(2)

class config:
    bdport = int(cfg['LocalPort'])
    sip = str(cfg['ServerIpAddress'])
    sport = int(cfg['ServerPort'])
    max = int(cfg['Maxmium'])
    check = bool(cfg['WCheck'])
    motd = str(cfg['MotdMsg'])
    bic = bool(cfg['BypassIpCheck'])

class PacketBuffer:

    def __init__(self):
        self.bytes = BytesIO()

    def send(self, value):
        self.bytes.write(value)

    def get_writable(self):
        return self.bytes.getvalue()

    def reset_cursor(self):
        self.bytes.seek(0)

    def read(self, length=None):
        return self.bytes.read(length)

def send_varint(value, s):
    out = bytes()
    while 1:
        byte = value & 127
        value >>= 7
        out += struct.pack('B', byte | (128 if value > 0 else 0))
        if value == 0:
            break

    s.send(out)

def read_varint(f):
    number = 0
    bytes_encountered = 0
    while 1:
        byte = f.read(1)
        if len(byte) < 1:
            raise EOFError('Unexpected end of message.')
        byte = ord(byte)
        number |= (byte & 127) << 7 * bytes_encountered
        if not byte & 128:
            break
        bytes_encountered += 1
        if bytes_encountered > 5:
            raise ValueError('Tried to read too long of a VarInt')

    return number

def send_string(value, s):
    value = value.encode('utf-8')
    send_varint(len(value), s)
    s.send(value)

def read_string(f):
    leng = read_varint(f)
    return f.read(leng).decode('utf-8')

def send_unsigned_short(value, s):
    s.send(struct.pack('>H', value))

def read_ushort(value):
    return struct.unpack('>H', value.read(2))[0]

def read_bytearray(f):
    leng = read_varint(f)
    return struct.unpack(str(leng) + 's', f.read(leng))[0]

def handshake(s, host, port, state,):
    packet_buffer = PacketBuffer()
    send_varint(0, packet_buffer)
    send_varint(47, packet_buffer)
    send_string(host, packet_buffer)
    send_unsigned_short(port, packet_buffer)
    send_varint(state, packet_buffer)
    send_varint(len(packet_buffer.get_writable()), s)
    s.send(packet_buffer.get_writable())

def login_start(s, name):
    packet_buffer = PacketBuffer()
    send_varint(0, packet_buffer)
    send_string(name, packet_buffer)
    send_varint(len(packet_buffer.get_writable()), s)
    s.send(packet_buffer.get_writable())

def read_packet(stream):
    length = read_varint(stream)
    packet_data = PacketBuffer()
    packet_data.send(stream.read(length))
    while len(packet_data.get_writable()) < length:
        packet_data.send(stream.read(length - len(packet_data.get_writable())))
    packet_data.reset_cursor()
    return packet_data

Zser = config.sip
Port = config.sport

def mode1(conn, conn1):
    while True:
        try:
            data = conn.recv(4096)
            if data == b'':
                break
            conn1.send(data)
        except (ConnectionAbortedError, ConnectionResetError):
            break
        except:
            print('Unexpected Error!')
            with open('logs/errorlog.log', 'a+') as elog:
                traceback.print_exc(file=elog)
            break
    conn.close()
    conn1.close()

def SendPRes(s):
    packet_buffer = PacketBuffer()
    send_varint(0, packet_buffer)
    send_string(config.motd, packet_buffer)
    send_varint(len(packet_buffer.get_writable()), s)
    s.send(packet_buffer.get_writable())
    data = s.recv(4096)
    s.send(data)
    s.close()

def SendBRes(s):
    packet_buffer = PacketBuffer()
    send_varint(0, packet_buffer)
    send_string('''{
    "text": "你不在白名单内",
    "color": "dark_red",
    "bold": "true",
    }''', packet_buffer)
    send_varint(len(packet_buffer.get_writable()), s)
    s.send(packet_buffer.get_writable())
    s.close()

try:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', config.bdport))
    server.listen(config.max)
    print('服务器开启成功!')
except:
    print('服务器开启失败!请检测端口是否被占用等问题!')
    sleep(5)
    exit()

while True:
    try:
        conn, addr = server.accept()
        Data = conn.recv(4096)
        packet_data = BytesIO(Data)
        plength = read_varint(packet_data)
        packet_id = read_varint(packet_data)
        if packet_id == 0:
            fn = False
            plv = read_varint(packet_data)
            address = read_string(packet_data)
            port = read_ushort(packet_data)
            state = read_varint(packet_data)
            try:
                plen = read_ushort(packet_data)
                name = read_string(packet_data)
            except:
                fn = True
            if state == 1:
                print(f'{addr[0]} Pinged')
                with open('logs/normal.log', 'a+') as log:
                    log.write(f'[{datetime.today()}]{addr[0]} Pinged\n')
                SendPRes(conn)
            elif state == 2:
                if fn:
                    data = conn.recv(4096)
                    packetdata = read_packet(BytesIO(data))
                    id = read_varint(packetdata)
                    name = read_string(packetdata)
                if config.check:
                    namelist = open('list.txt', 'r').read().split('\n')
                    permis = False
                    for Name in namelist:
                        if Name == name:
                            permis = Name
                            break
                    if not permis:
                        SendBRes(conn)
                        print(f'{name} is not in Whitelist!')
                        with open('logs/normal.log', 'a+') as log:
                            log.write(f'[{datetime.today()}]{name} is not in Whitelist!\n')
                        continue
                print(f'{name}已连接!')
                with open('logs/normal.log', 'a+') as log:
                    log.write(f'[{datetime.today()}]{name}已连接!\n')
                gser = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                gser.connect((Zser, Port))
                if config.bic:
                    Zser = 'mc.hypixel.net'
                    Port = 25565
                handshake(gser, Zser, Port, 2)
                login_start(gser, name)
                Thread(target=mode1, args=(conn, gser,), daemon=True).start()
                Thread(target=mode1, args=(gser, conn,), daemon=True).start()
    except (ConnectionResetError, ConnectionAbortedError):
        conn.close()
    except:
        print('Unexpected Error!')
        with open('logs/errorlog.log', 'a+') as elog:
            traceback.print_exc(file=elog)
        conn.close()



