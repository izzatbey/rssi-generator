import argparse
import csv
import math
import os
import time
from random import seed
import xlrd
from tempfile import TemporaryFile
from xlwt import Workbook
from comm.socket_comm import socketrecv, socketsend


print("\n================================= BCH CODE ===============================\n")
start=time.time()

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Data quantification using Jana Multibit process.')
parser.add_argument('--datapathNode', required=True, help='Path to the preprocess directory')
parser.add_argument('--filenameNode', required=True, help='filename of the preprocess')
parser.add_argument('--datapathGateway', required=True, help='Path to the preprocess directory')
parser.add_argument('--filenameGateway', required=True, help='filename of the preprocess')
parser.add_argument('--destination', required=True, help='Path for the result destination')
args = parser.parse_args()

data_file_path_node = os.path.join(args.datapathNode, args.filenameNode)
data_file_path_gateway = os.path.join(args.datapathGateway, args.filenameGateway)


def load_data_from_csv(file_path):
    with open(file_path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        next(csv_reader)
        data = [row[0] for row in csv_reader]
    return data

data_kuantisasi_node = load_data_from_csv(data_file_path_node)
data_kuantisasi_gateway = load_data_from_csv(data_file_path_gateway)

# Calculate KDR Kuantisasi ALICE - BOB
errkuan = [i+1 for i, (node_value, gateway_value) in enumerate(zip(data_kuantisasi_node, data_kuantisasi_gateway)) if node_value != gateway_value]
kdrkuan = len(errkuan) / len(data_kuantisasi_node)
print("KDR Kuantisasi ALICE - BOB = %.2f%%" % (kdrkuan * 100))

alalice = []
bobob = []
deleteblok = 0
m = 5
n = 2**m-1  # codeword length (n = 2^m - 1 = 31)
k = 6  # information bits
t = 7  # correcting capability
#m = 7
# n = 2**m-1 # codeword length (n = 2^m - 1 = 31)
# k = 50 # information bits
# t = 13 # correcting capability
maks = math.floor(len(data_kuantisasi_node) / k)
alice = []
bob = []
for i in range(0, int(maks)):
    alice.append(data_kuantisasi_node[(k * i):(k * (i + 1))])
    bob.append(data_kuantisasi_gateway[(k * i):(k * (i + 1))])
# ------------------- GF-ARITHMETIC --------------------
# ------------------------------------------------------
def gf_add(a, b):
    prod = ""
    if len(a) > len(b):
        b = '0'*(len(a) - len(b)) + b
    elif len(a) < len(b):
        a = '0'*(len(b) - len(a)) + a
    for i in range(len(a)):
        # XOR
        if a[i] == b[i]:
            prod += '0'
        else:
            prod += '1'
    return prod


def gf_mul(a, b):
    prod = '0'*(len(a) + len(b) - 1)
    for i in range(len(a)):
        for j in range(len(b)):
            # prod[i+j] ^= a[i] * b[j]
            # Multiplication
            if a[i] == '0' or b[j] == '0':
                tmp = '0'
            else:
                tmp = '1'
            # XOR
            if prod[i+j] == tmp:
                prod = prod[:i+j] + '0' + prod[i+j+1:]
            else:
                prod = prod[:i+j] + '1' + prod[i+j+1:]
    return prod


def gf_xor(a, b):
    prod = ""
    for i in range(1, len(b)):
        # XOR
        if a[i] == b[i]:
            prod += '0'
        else:
            prod += '1'
    return prod


def gf_div(a, b, mode=0):
    # mode 0: return remainder
    # mode 1: return quotient
    pick = len(b)
    q = ""       # quotient
    r = a[:pick]  # remainder
    while pick < len(a):
        if r[0] == '1':
            q += '1'
            r = gf_xor(b, r) + a[pick]
        else:
            q += '0'
            r = gf_xor('0'*pick, r) + a[pick]
        pick += 1
    if r[0] == '1':
        q += '1'
        r = gf_xor(b, r)
    else:
        q += '0'
        r = gf_xor('0'*pick, r)
    if not mode:
        return r
    return q
# ------------------- CODER/DECODER --------------------
# ------------------------------------------------------
# Encoding method: c(x) = data(x) * g(x)


def bch_encode(data, g):
    return gf_mul(data, g)
# Decoding method: polynomial division (while-loop, shifting until w <= t)


def bch_decode(c, g):
    syndrome = gf_div(c, g)
    if not weight(syndrome):
        return c
    cnt_rot = 0
    recd = c
    stp = 0
    while weight(syndrome) > t:
        ##        print('ada sindrom %d , loop ke %d'%(weight(syndrome),(stp+1)))
        recd = l_rotate(recd)
        syndrome = gf_div(recd, g)
        cnt_rot += 1
        stp += 1
        if stp > n:
            break
##    print('Done, sindrom %d'%(weight(syndrome)))
    recd = gf_add(recd, syndrome)
    recd = r_rotate(recd, cnt_rot)
    return recd
# --------------------- UTILITIES ----------------------
# ------------------------------------------------------


def l_rotate(poly, s=1):
    return poly[s:] + poly[:s]


def r_rotate(poly, s=1):
    return poly[-s:] + poly[:-s]


def weight(poly):
    return sum([int(coeff) for coeff in poly])


def polynomial(poly):
    for coeff in range(len(poly)):
        if (poly[coeff] != '0'):
            if (coeff != len(poly)-1):
                print("x^" + str(len(poly)-coeff-1) + " + ", end="")
            else:
                print("1", end="")
    print()


# ------------------------ MAIN ------------------------
# ------------------------------------------------------
global totalerrorbch
totalerrorbch = []
global parityalice
parityalice = []


def main(data, data2, z):
    global deleteblok
    seed()

    # g = "1101111100110100001110101101100111" # g(x) BCH(63,30) t=6 m=6 k=30
    g = "11001011011110101000100111"  # BCH (31,6) m=5 k=6 t=7
     #g = "10010110111" # generating polynomial g(x), of the (31,21) BCH code x^10 + x^9 + x^8 + x^6 + x^5 + x^3 + 1 t=2 m=5 k=21
    # g = "111010001" # g(x) BCH(15,7) t=2 m=4 k=7
    # g = "100010001100000101100010001010100000001100110110010101010100101011001001001101" #BCH(127,50) t=13 m=7 k=50
    # g = "110101101010110101011010110110011001111000111011011110" #bch(63,10) t=13 m=6 k=10
    c1 = bch_encode(data, g)  # codeword c(x)
    c2 = bch_encode(data2, g)

    errcode = 0
    poserrcode = []
    for i in range(n-k):
        if c1[i+k] != c2[i+k]:
            errcode = errcode+1
            poserrcode.append(i+k)
    totalerrorbch.append(errcode)
    parityalice.append(c1[k:])
    if errcode <= t:
        for i in range(errcode):
            if c2[poserrcode[i]] == '1':
                c2 = c2[:poserrcode[i]] + '0' + c2[poserrcode[i]+1:]
            else:
                c2 = c2[:poserrcode[i]] + '1' + c2[poserrcode[i]+1:]

        recd1 = bch_decode(c1, g)
        recd2 = bch_decode(c2, g)
        recd1 = gf_div(recd1, g, 1)
        recd2 = gf_div(recd2, g, 1)
        alalice.append(recd1)
        bobob.append(recd2)
    else:
        deleteblok += 1


# ----------------------- START ------------------------
# ------------------------------------------------------
for i in range(int(maks)):
    # print('\n##################### Blok ke %d #####################'%(i+1))
    dt1 = ''.join(str(e) for e in alice[i])
    dt2 = ''.join(str(e) for e in bob[i])
    main(dt1, dt2, i+1)
# for i in range(len(parityalice)):
##    print('[{}] {}'.format(i+1,parityalice[i]))
alice11 = ''.join(alalice)
bob11 = ''.join(bobob)
bitalice = list(map(int, alice11))
bitbob = list(map(int, bob11))

salah = 0
for i in range(len(bitalice)):
    if bitalice[i] != bitbob[i]:
        salah += 1

r1= len(data_kuantisasi_node)
r2= len(bitalice)
errbchbefore = []
i = 0
while i < len(data_kuantisasi_node):
    if (data_kuantisasi_node[i] == data_kuantisasi_gateway[i]):
        i = i+1
    else:
        errbchbefore.append(i+1)
        i = i+1
errbch=[]
for i in range(len(bitalice)):
    if (bitalice[i]==bitbob[i]):
        i=i+1
    else:
        errbch.append(i+1)

kdrbch=len(errbch)/len(bitalice)

print('BCH jumlah blok error = %d, \nJumlah blok dikoreksi = %d, \nKDR = %f' %(deleteblok,(maks-deleteblok),kdrbch))
print('Jumlah delete blok = %d dari %d blok, \nTotal bit = %d sebelumnya %d , \nTotal error = %d\n'%(deleteblok,maks,len(bitalice),maks*k,sum(totalerrorbch)))
print('Bit proses = %d'%(maks*k))
print('Blok = %d'%maks)
print('Total error = %d'%(sum(totalerrorbch)))
print('Blok koreksi = %d'%(maks-deleteblok))

print('Del blok = %d'%deleteblok)
print('JUMLAH BIT HASIL BCH CODE BOB %d'%len(bitalice))

# Saving BCH
output_file_path = os.path.join(args.destination, 'Hasil_BCH_31,6_Gateway.csv')

with open(output_file_path, 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)

    for i in range(len(bitalice)):
        csv_writer.writerow([bitalice[i]])

end = time.time()
waktu_bch = end - start
print("Saved BCH results to:", output_file_path)
print("Waktu Eksekusi : ", waktu_bch)
print("BCH CODE Berhasil")