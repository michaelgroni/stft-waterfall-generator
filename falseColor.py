def falseColorScreen(gray):
    '''
    Convenience function, returns falseColor(gray, [ [0, 0, 24], [128, 128, 255], [0, 255, 0], [255, 0, 0] ]).
    '''
    return falseColor(gray, [ [0, 0, 24], [64, 64 , 255], [150, 150, 255], [255, 255, 255], [255, 255, 0] ])
    
    
def falseColorPrint(gray):
    '''
    Convenience function, returns falseColor(gray, [ [255, 255, 255], [128, 128, 128], [64 , 64, 64], [128, 64, 0], [192, 0, 0] ]).
    '''
    return falseColor(gray, [ [255, 255, 255], [128, 128, 128], [64 , 64, 64], [128, 64, 0], [192, 0, 0] ])


def falseColor(gray, colors):
    '''
    This function takes a gray value between 0 and 255 (integer or floating point) and an array of
    four rgb colors, e.g. [ [228, 228, 228], [192, 192, 192], [255, 255, 128], [255, 0, 0], [128, 0, 0] ]. The
    first color stands for the lowest gray value and the last one for the highest.
    
    Returns a bytearray with values for red, green and blue.
    '''
    if gray<0 or gray>255:
        raise ValueError('Gray must be between 0 and 255. The value of gray was {}'.format(gray))
    if len(colors)!=5:
        raise ValueError('Need five RGB colors. The length of colors was {}'.format(len(colors)))


    # select an interval between two colours based on the gray value
    # and calculate the distance to the lower color between 0 and 1
    if gray<=64:
        color1 = colors[0]
        color2 = colors[1]
        distance = gray/64.0
    elif gray<=128:
        color1 = colors[1]
        color2 = colors[2]
        distance = (gray-64)/64.0
    elif gray<=192:
        color1 = colors[2]
        color2 = colors[3]
        distance = (gray-128)/64.0
    else:
        color1 = colors[3]
        color2 = colors[4]
        distance = (gray-192)/64.0
    
    # interpolation
    red =   int ((color1[0]*(1-distance) + color2[0]*distance))
    green = int ((color1[1]*(1-distance) + color2[1]*distance))
    blue =  int ((color1[2]*(1-distance) + color2[2]*distance))
          
    # make bytearray from integers
    rgb = bytearray();
    rgb.append(red.to_bytes(1, byteorder='big')[0])
    rgb.append(green.to_bytes(1, byteorder='big')[0])
    rgb.append(blue.to_bytes(1, byteorder='big')[0])
    
    return rgb.copy();
