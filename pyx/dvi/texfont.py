from pyx import pykpathsea, canvas
import tfmfile, vffile
from pyx.font import font, t1file

class TeXfont:

    def __init__(self, name, c, q, d, tfmconv, pyxconv, debug=0):
        self.name = name
        self.q = q                  # desired size of font (fix_word) in TeX points
        self.d = d                  # design size of font (fix_word) in TeX points
        self.tfmconv = tfmconv      # conversion factor from tfm units to dvi units
        self.pyxconv = pyxconv      # conversion factor from dvi units to PostScript points
        tfmpath = pykpathsea.find_file("%s.tfm" % self.name, pykpathsea.kpse_tfm_format)
        if not tfmpath:
            raise TFMError("cannot find %s.tfm" % self.name)
        self.TFMfile = tfmfile.TFMfile(tfmpath, debug)

        # We only check for equality of font checksums if none of them
        # is zero. The case c == 0 happend in some VF files and
        # according to the VFtoVP documentation, paragraph 40, a check
        # is only performed if TFMfile.checksum > 0. Anyhow, being
        # more generous here seems to be reasonable
        if self.TFMfile.checksum != c and self.TFMfile.checksum != 0 and c != 0:
            raise DVIError("check sums do not agree: %d vs. %d" %
                           (self.TFMfile.checksum, c))

        # Check whether the given design size matches the one defined in the tfm file
        if abs(self.TFMfile.designsize - d) > 2:
            raise DVIError("design sizes do not agree: %d vs. %d" % (self.TFMfile.designsize, d))
        #if q < 0 or q > 134217728:
        #    raise DVIError("font '%s' not loaded: bad scale" % self.name)
        if d < 0 or d > 134217728:
            raise DVIError("font '%s' not loaded: bad design size" % self.name)

        self.scale = 1.0*q/d

    def fontinfo(self):
        class fontinfo:
            pass

        # The following code is a very crude way to obtain the information
        # required for the PDF font descritor. (TODO: The correct way would
        # be to read the information from the AFM file.)
        fontinfo = fontinfo()
        try:
            fontinfo.fontbbox = (0,
                                 -self.getdepth_ds(ord("y")),
                                 self.getwidth_ds(ord("W")),
                                 self.getheight_ds(ord("H")))
        except:
            fontinfo.fontbbox = (0, -10, 100, 100)
        try:
            fontinfo.italicangle = -180/math.pi*math.atan(self.TFMfile.param[0]/65536.0)
        except IndexError:
            fontinfo.italicangle = 0
        fontinfo.ascent = fontinfo.fontbbox[3]
        fontinfo.descent = fontinfo.fontbbox[1]
        try:
            fontinfo.capheight = self.getheight_ds(ord("h"))
        except:
            fontinfo.capheight = 100
        try:
            fontinfo.vstem = self.getwidth_ds(ord("."))/3
        except:
            fontinfo.vstem = 5
        return fontinfo

    def __str__(self):
        return "font %s designed at %g TeX pts used at %g TeX pts" % (self.name, 
                                                                      16.0*self.d/16777216L,
                                                                      16.0*self.q/16777216L)

    def getsize_pt(self):
        """ return size of font in (PS) points """
        # The factor 16L/16777216L=2**(-20) converts a fix_word (here self.q)
        # to the corresponding float. Furthermore, we have to convert from TeX
        # points to points, hence the factor 72/72.27.
        return 16L*self.q/16777216L*72/72.27

    def _convert_tfm_to_dvi(self, length):
        # doing the integer math with long integers will lead to different roundings
        # return 16*length*int(round(self.q*self.tfmconv))/16777216

        # Knuth instead suggests the following algorithm based on 4 byte integer logic only
        # z = int(round(self.q*self.tfmconv))
        # b0, b1, b2, b3 = [ord(c) for c in struct.pack(">L", length)]
        # assert b0 == 0 or b0 == 255
        # shift = 4
        # while z >= 8388608:
        #     z >>= 1
        #     shift -= 1
        # assert shift >= 0
        # result = ( ( ( ( ( b3 * z ) >> 8 ) + ( b2 * z ) ) >> 8 ) + ( b1 * z ) ) >> shift
        # if b0 == 255:
        #     result = result - (z << (8-shift))

        # however, we can simplify this using a single long integer multiplication,
        # but take into account the transformation of z
        z = int(round(self.q*self.tfmconv))
        assert -16777216 <= length < 16777216 # -(1 << 24) <= length < (1 << 24)
        assert z < 134217728 # 1 << 27
        shift = 20 # 1 << 20
        while z >= 8388608: # 1 << 23
            z >>= 1
            shift -= 1
        # length*z is a long integer, but the result will be a regular integer
        return int(length*long(z) >> shift)

    def _convert_tfm_to_ds(self, length):
        return (16*long(round(length*float(self.q)*self.tfmconv))/16777216) * self.pyxconv * 1000 / self.getsize_pt()
    
    def _convert_tfm_to_pt(self, length):
        return (16*long(round(length*float(self.q)*self.tfmconv))/16777216) * self.pyxconv

    # routines returning lengths as integers in dvi units

    def getwidth_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.width[self.TFMfile.char_info[charcode].width_index])

    def getheight_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.height[self.TFMfile.char_info[charcode].height_index])

    def getdepth_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.depth[self.TFMfile.char_info[charcode].depth_index])

    def getitalic_dvi(self, charcode):
        return self._convert_tfm_to_dvi(self.TFMfile.italic[self.TFMfile.char_info[charcode].italic_index])

    # routines returning lengths as integers in design size (AFM) units 

    def getwidth_ds(self, charcode):
        return self._convert_tfm_to_ds(self.TFMfile.width[self.TFMfile.char_info[charcode].width_index])

    def getheight_ds(self, charcode):
        return self._convert_tfm_to_ds(self.TFMfile.height[self.TFMfile.char_info[charcode].height_index])

    def getdepth_ds(self, charcode):
        return self._convert_tfm_to_ds(self.TFMfile.depth[self.TFMfile.char_info[charcode].depth_index])

    def getitalic_ds(self, charcode):
        return self._convert_tfm_to_ds(self.TFMfile.italic[self.TFMfile.char_info[charcode].italic_index])

    # routines returning lengths as floats in PostScript points

    def getwidth_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.width[self.TFMfile.char_info[charcode].width_index])

    def getheight_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.height[self.TFMfile.char_info[charcode].height_index])

    def getdepth_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.depth[self.TFMfile.char_info[charcode].depth_index])

    def getitalic_pt(self, charcode):
        return self._convert_tfm_to_pt(self.TFMfile.italic[self.TFMfile.char_info[charcode].italic_index])

    def text_pt(self, x_pt, y_pt, charcodes):
        return TeXtext_pt(self, x_pt, y_pt, charcodes, self.getsize_pt())

    def getMAPline(self, fontmap):
        if self.name not in fontmap:
            raise RuntimeError("missing font information for '%s'; check fontmapping file(s)" % self.name)
        return fontmap[self.name]


class virtualfont(TeXfont):

    def __init__(self, name, path, c, q, d, tfmconv, pyxconv, debug=0):
        TeXfont.__init__(self, name, c, q, d, tfmconv, pyxconv, debug)
        self.vffile = vffile.vffile(path, self.scale, tfmconv, pyxconv, debug > 1)

    def getfonts(self):
        """ return fonts used in virtual font itself """
        return self.vffile.getfonts()

    def getchar(self, cc):
        """ return dvi chunk corresponding to char code cc """
        return self.vffile.getchar(cc)

    def text_pt(self, x_pt, y_pt, charcodes):
        raise RuntimeError("you don't know what you're doing")


class TeXtext_pt(canvas.canvasitem):

    def __init__(self, font, x_pt, y_pt, charcodes, size_pt):
        self.font = font
        self.x_pt = x_pt
        self.y_pt = y_pt
        self.charcodes = charcodes
	self.size_pt = size_pt

    def processPS(self, file, writer, context, registry, bbox):
        mapline = self.font.getMAPline(writer.getfontmap())
	font = mapline.getfont()
	text = font.text_pt(self.x_pt, self.y_pt, self.charcodes, self.size_pt, decoding=mapline.getencoding(), slant=mapline.slant)
	text.processPS(file, writer, context, registry, bbox)

    def processPDF(self, file, writer, context, registry, bbox):
        pass
