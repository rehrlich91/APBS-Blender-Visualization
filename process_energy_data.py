import multiprocessing
import sys
import glob
import pathlib
import pandas as pd
import seaborn as sns
import time
import matplotlib as mpl
import argparse
import numpy as np
from readDX import processDX

###############################################################################

def colorFader(c1,c2,mix=0): #fade (linear interpolate) from color c1 (at mix=0) to c2 (mix=1)
    c1=np.array(mpl.colors.to_rgb(c1))
    c2=np.array(mpl.colors.to_rgb(c2))
    return(mpl.colors.to_hex((1-mix)*c1 + mix*c2))

###############################################################################

def getRGB(c1, c2, nbins):
    colors = []
    for x in range(nbins + 1):
        hex = colorFader(c1, c2, x / nbins)
        rgbCol = mpl.colors.to_rgb(hex)
        colors.append('_'.join(map(str, rgbCol)))
    return(colors)

###############################################################################

def binDF(results):
    newRes = []
    bins = [-500, -50, -30, -20, -17.5, -15, -12.5, -10, -9, -8, -7, -6, -5, -4, -3, -2, -1,
             -0.8, -0.6, -0.5, -0.4, -0.3, -0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5,
            0.6, 0.8, 1, 1.5, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12.5, 15, 17.5, 20, 30, 50, 500]
    nc1, nc2 = '#0F00FF', '#ADAFFF'
    pc1, pc2 = '#FFADAD', '#FF0000'
    lbins = len(bins)
    ncolors = getRGB(nc1, nc2, int((lbins/2) - 1))
    pcolors = getRGB(pc1, pc2, int((lbins/2) - 1))
    colors = ncolors + pcolors
    del colors[25]
    for i in results:
        id, df = i[0], i[1]
        df['binned'] = pd.cut(df['energy'], bins=bins, labels=colors)
        df[['r', 'g', 'b']] = df['binned'].str.split('_', expand=True)
        df = df.drop(['binned'], axis=1)
        df['alpha'] = '0.75'
        newRes.append([id, df])
    return(newRes)

###############################################################################

def to_csv(results):
    pathlib.Path('test_rgb/').mkdir(parents=True, exist_ok=True)
    for i in results:
        id, df = i[0], i[1]
        ind = id.rfind('/')
        id_ = id[ind + 1:-3]
        outName = 'test_rgb/%s.csv' %(id_)
        df.to_csv(outName, index=False)

###############################################################################

def parse_args():
    parser = argparse.ArgumentParser()
    cores_default = multiprocessing.cpu_count() - 2
    parser.add_argument('-mif', '--input', action='store', help='folder of *.dat files', type=str)
    parser.add_argument('-a', '--analysis', action='store', help='apbs or easymifs', type=str)
    parser.add_argument('-c', '--cores', action='store', help='number of cores to use', type=int)
    return parser.parse_args()

###############################################################################
#           Main Program                                                      #
###############################################################################

if __name__ == '__main__':
    start = time.time()
    args = parse_args()         # gather arugments
    pathDX = "%s/*.dx" % (''.join(glob.glob(args.input)))  # path to *.dx folder
    input_filesDX = sorted(glob.glob(pathDX))
    results = processDX(input_filesDX, args.analysis, args.cores, False)
    newRes = binDF(results)
    to_csv(newRes)




