### =============================================================================
### This script presents a module to create an HDR image from LDR images.
### The script automatically reads the exposure time of LDR images in a user-defined folder.
### The script uses OpenCV and exiftool modules.   
### The script is adopted from the following links:
### https://docs.opencv.org/3.4/d2/df0/tutorial_py_hdr.html 
### https://docs.opencv.org/3.4/d3/db7/tutorial_hdr_imaging.html
### https://learnopencv.com/high-dynamic-range-hdr-imaging-using-opencv-cpp-python/

import os
import cv2
import numpy as np
import subprocess
import natsort
### must define the path to exif tool
### exifToolPath  = r'C:\Program Files\ExifTool\exiftool.exe'

class HDRGenerator:
    ### this init mehtod sets the location to store the HDR image and tonemap image
    def __init__(self, LDRIs_path, LDRI_ext, exifToolPath, ResultFolderPath=None):
        self.exifToolPath=exifToolPath
        self.LDRIs_path = LDRIs_path
        self.LDRI_ext = LDRI_ext
        if ResultFolderPath==None:
            Resultfoldername = 'Analysis_Results'
            self.ResultFolder = os.path.join(LDRIs_path, Resultfoldername)
        else:
            self.ResultFolder=ResultFolderPath
        if not os.path.exists(self.ResultFolder):
            os.makedirs(self.ResultFolder)
    ## this method reads the list of images and their exposure times
    ## returns an image array list and an exposure time array list
    def readImagesAndTimes(self):
        ### read image file list
        LDRIs_filelist = natsort.natsorted([os.path.join(self.LDRIs_path, ldr) for ldr in os.listdir(self.LDRIs_path) if ldr.endswith(self.LDRI_ext)], reverse=False)
        print(LDRIs_filelist)

        no_ldrs = len(LDRIs_filelist)
        Exposuretime  = np.zeros(no_ldrs, dtype=np.float32)
        
        for n in range(0, no_ldrs):
            input_file = LDRIs_filelist[n]
            process = subprocess.Popen([self.exifToolPath, input_file], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            infoDict = {}
            for tag in process.stdout:
                line = tag.strip().split(':')
                infoDict[line[0].strip()] = line[-1].strip()
                
            Etimes=infoDict["Exposure Time"]
            Evalue = eval('/'.join(map(str,map(float,Etimes.split("/")))))
            Exposuretime [n] = Evalue
            
        print(Exposuretime)
        images = []
        for filename in LDRIs_filelist:
            im = cv2.imread(filename)
            images.append(im)
            
        return images, Exposuretime    

    ## this methods generate an hdr image with two tone mapped images from a set of LDR images
    ## returns three arrays of HDR and LDR images
    def generateHDRIandTonemap(self, CRF_filepath=None, Output_filename=None, **tonemap_param):
        images, Exposuretime  = self.readImagesAndTimes()

        ### aligne LDR images   
        print("Aligning images ... ")
        alignMTB = cv2.createAlignMTB()
        alignMTB.process(images, images)

        if CRF_filepath==None:
            camera_res = 'CRF.txt'
            ### get the camera repsonse function
            os.path.join(self.LDRIs_path, camera_res)
            ### If the camera response function is not available, then calculate and store it.
            print('Calculating and writing the camera response function...') 
            calibrateDebevec = cv2.createCalibrateDebevec()
            responseDebevec = calibrateDebevec.process(images, Exposuretime)

            with open(os.path.join(self.LDRIs_path, camera_res), 'w') as outfile:
                outfile.write('# Array shape: {0}\n'.format(responseDebevec.shape))
                for res_fun_slice in responseDebevec:
                    np.savetxt(outfile, res_fun_slice, fmt='%10.7f')
                    outfile.write('# New slice\n')
        else:
            ### Read the camera response function if it is available. 
            print('Reading the existing camera response function...')  
            responseDebevec  = np.loadtxt(CRF_filepath)
            responseDebevec = responseDebevec.reshape((256,1,3))
            responseDebevec = np.float32(responseDebevec)

        ### Merge LDR images
        mergeDebevec = cv2.createMergeDebevec()
        hdrDebevec = mergeDebevec.process(images, Exposuretime, responseDebevec)

        ### Save the HDR image
        if Output_filename==None:
            Output_HDRI = "hdrDebevec.hdr"
            tonmapGamma_filename = "tm_Gamma_hdrDebevec" + ".jpg"
            tonmapRein_filename = "tm_Reinhard_hdrDebevec" + ".jpg"
        else:
            Output_HDRI = Output_filename + '.hdr'
            tonmapGamma_filename = "tm_Gamma_" + Output_filename + ".jpg"
            tonmapRein_filename = "tm_Reinhard_" + Output_filename + ".jpg"

        cv2.imwrite(os.path.join(self.ResultFolder, Output_HDRI), hdrDebevec)
        print("Saved the HDR image")
        ### Tonemap the generated HDR image

        print(" >>> Tonemap using gamma method ... ")
        tonemap_Gamma = cv2.createTonemap(tonemap_param['gammavalue'])
        ldrGamma = tonemap_Gamma.process(hdrDebevec)
        ldrGamma_8bit = np.clip(ldrGamma*255, 0, 255).astype('uint8')
        cv2.imwrite(os.path.join(self.ResultFolder, tonmapGamma_filename), ldrGamma_8bit)
        print("saved Gamma tone mapped image")

        print(" >>> Tonemap using Reinhard's method ... ")
        # Parameters
        # gamma	gamma value for gamma correction. 
        # intensity	result intensity in [-8, 8] range. Greater intensity produces brighter results.
        # light_adapt	light adaptation in [0, 1] range. If 1 adaptation is based only on pixel value, if 0 it's global, otherwise it's a weighted mean of this two cases.
        # color_adapt	chromatic adaptation in [0, 1] range. If 1 channels are treated independently, if 0 adaptation level is the same for each channel.
        tonemapReinhard = cv2.createTonemapReinhard(tonemap_param['Rein_gamma'], tonemap_param['Rein_intensity'],
                                                    tonemap_param['Rein_light_adapt'], tonemap_param['Rein_color_adapt'])
        ldrReinhard = tonemapReinhard.process(hdrDebevec)
        ldrReinhard_8bit = np.clip(ldrReinhard*255, 0, 255).astype('uint8')
        cv2.imwrite(os.path.join(self.ResultFolder, tonmapRein_filename), ldrReinhard_8bit)
        print("saved Reinhard tone mapped image")
        return hdrDebevec, ldrGamma_8bit, ldrReinhard_8bit
