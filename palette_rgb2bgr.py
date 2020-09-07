with open('d:/temp/totala1/palettes/PALETTE.PAL','rb') as file:
    data_rgbx = file.read()

acc = []
data_bgrx = []
for n,byte in enumerate(data_rgbx):
    acc += [byte]
    if len(acc)==4:
        data_bgrx += [acc[2], acc[1], acc[0], acc[3]]
        acc = []

with open('PALETTE_BGRX.PAL','wb') as file:
    file.write(bytes(data_bgrx))

