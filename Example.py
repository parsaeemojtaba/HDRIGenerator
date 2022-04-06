### =============================================================================
### This script shows an example of creating HDR image using HDRGenerator module

from HDRI_Generator import HDRGenerator
### define the path to exif tool
exifToolPath  = r'C:\Program Files\ExifTool\exiftool.exe'

### define the path to the camera response function 
### otherwise the camera response function will be calculated and stored alongside LDR images
CRF_filepath=r'C:\.....\CRF.txt'

### define the path to the LDR images directory.
LDRIs_path = r'C:\......\imagefolder'

### determine the extension of the LDR images
LDRI_ext = '.jpg'

### output file name
Output_filename = 'pm'

tonemap_param = {
        "gammavalue" : 2.2,
        "Rein_gamma" : 1,
        "Rein_intensity" : 1,
        "Rein_light_adapt" : 0,
        "Rein_color_adapt" : 0,
        }

HDRIGen=HDRGenerator(LDRIs_path, LDRI_ext, exifToolPath)
HDRIGen.generateHDRIandTonemap( CRF_filepath, Output_filename, **tonemap_param)
