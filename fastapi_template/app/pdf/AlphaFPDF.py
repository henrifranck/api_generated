#!/usr/bin/env python3
# Ported from PHP to Python / pyFPDF2 in 2021 by Björn Seipel
# Original Author: Martin Hall-May
# License: FPDF
# http://www.fpdf.org/en/script/script74.php

from math import cos, pi, radians, sin, tan

from fpdf import FPDF, util


class AlphaFPDF(FPDF):
    _extgstates = {}

    # alpha: real value from 0 (transparent) to 1 (opaque)
    # bm:    blend mode, one of the following:
    #          Normal, Multiply, Screen, Overlay, Darken, Lighten, ColorDodge, ColorBurn,
    #          HardLight, SoftLight, Difference, Exclusion, Hue, Saturation, Color, Luminosity
    def set_alpha(self, alpha, bm="Normal"):
        if alpha < 0:
            alpha = 0
        if alpha > 1:
            alpha = 1
        # set alpha for stroking (CA) and non-stroking (ca) operations
        gs = self.add_ext_gs_state({"ca": alpha, "CA": alpha, "BM": "/" + bm})
        self.set_ext_gs_state(gs)

    def add_ext_gs_state(self, parms):
        n = len(self._extgstates) + 1
        self._extgstates[n] = {"parms": parms}

        return n

    def set_ext_gs_state(self, gs):
        self._out("/GS%d gs" % gs)

    def _enddoc(self):
        if len(self._extgstates) > 0 and float(self.pdf_version) < float(1.4):
            self.pdf_version = "1.4"
        FPDF._enddoc(self)

    def _putextgstates(self):
        for i in range(1, len(self._extgstates) + 1):
            self._newobj()
            self._extgstates[i]["n"] = self.n
            self._out("<</Type /ExtGState")
            parms = self._extgstates[i]["parms"]
            self._out("/ca %.2f" % parms["ca"])
            self._out("/CA %.2f" % parms["CA"])
            self._out("/BM " + parms["BM"])
            self._out(">>")
            self._out("endobj")

    def _putresourcedict(self):
        FPDF._putresourcedict(self)
        self._out("/ExtGState <<")
        for k, extgstate in zip(self._extgstates.keys(), self._extgstates.values()):
            self._out("/GS" + str(k) + " " + str(extgstate["n"]) + " 0 R")

        self._out(">>")

    def _putresources(self):
        self._putextgstates()
        FPDF._putresources(self)

    def _circle_text_transform(self, x, y, txt, tx=0, fy=0, tw=0, fw=0):

        fw += 90 + float(tw)
        tw *= pi / 180
        fw *= pi / 180

        if tx == "":
            tx = cos(float(tw))
        ty = sin(float(tw))
        fx = cos(float(fw))
        if fy == "":
            fy = sin(float(fw))

        s = "BT %.2f %.2f %.2f %.2f %.2f %.2f Tm (%s) Tj ET" % (
            tx,
            ty,
            fx,
            fy,
            x * self.k,
            (self.h - y) * self.k,
            util.escape_parens(txt),
        )
        s = f"q {self.text_color}  {s}  Q"

        self._out(s)

    def text_360(self, x=None, y=None, text=None, width=None):

        # set x, y to center of page if not set
        if x == None:
            x = self.w / 2
        if y == None:
            y = self.h / 2

        if text == None:
            return

        for non_printable in ("\n", "\t", "\r"):
            text = text.replace(non_printable, "")

        if len(text) == 0:
            return

        # set width to 1/2 width of text if not set
        if width == None:
            width = self.get_string_width(text) / 2

        value_degrees = 360 / len(text)

        cc = 1
        buffer = 1
        for temp in text:
            cc += 1
            st_x = cos((buffer * pi) / 180)
            st_target_x = x + (-st_x * width / 2)
            st_y = sin((buffer * pi) / 180)
            st_target_y = y + (-st_y * width / 2)

            self._circle_text_transform(
                st_target_x, st_target_y, temp, "", "", 90 - buffer
            )
            buffer += value_degrees

        if self.underline and text != "":
            # store line width
            line_width = self.line_width

            draw_color = str(self.text_color).upper()
            self._out(draw_color)

            lw = self.current_font["ut"] / 1000 * self.font_size_pt
            self.set_line_width(lw / 2)

            # draw circle
            circle_x = x - width / 2 + lw
            circle_y = y - width / 2 + lw
            circle_w = width - 2 * lw
            self.ellipse(circle_x, circle_y, circle_w, circle_w, style="D")

            # restore previous values
            self.set_line_width(line_width)
            self._out(self.draw_color)

    def start_transform(self):
        # save the current graphic state
        self._out("q")

    def scale_x(self, s_x, x="", y=""):
        self.scale(s_x, 100, x, y)

    def scale_y(self, s_y, x="", y=""):
        self.scale(100, s_y, x, y)

    def scale_xy(self, s, x="", y=""):
        self.scale(s, s, x, y)

    def scale(self, s_x, s_y, x="", y=""):
        if x == "":
            x = self.x
        if y == "":
            y = self.y
        if s_x == 0 or s_y == 0:
            raise ValueError("Please use values unequal to zero for Scaling")
        y = (self.h - y) * self.k
        x *= self.k
        # calculate elements of transformation matrix
        s_x /= 100
        s_y /= 100
        tm = [s_x, 0, 0, s_y, x * (1 - s_x), y * (1 - s_y)]

        # scale the coordinate system
        self.transform(tm)

    def mirror_h(self, x=""):
        self.scale(-100, 100, x)

    def mirror_v(self, y=""):
        self.scale(100, -100, "", y)

    def mirror_p(self, x="", y=""):
        self.scale(-100, -100, x, y)

    def mirror_l(self, angle=0, x="", y=""):
        self.scale(-100, 100, x, y)
        self.t_rotate(-2 * (angle - 90), x, y)

    def translate_x(self, t_x):
        self.translate(t_x, 0)

    def translate_y(self, t_y):
        self.translate(0, t_y)

    def translate(self, t_x, t_y):
        # calculate elements of transformation matrix
        tm = [1, 0, 0, 1, t_x * self.k, -t_y * self.k]
        # translate the coordinate system
        self.transform(tm)

    def t_rotate(self, angle, x="", y=""):
        if x == "":
            x = self.x
        if y == "":
            y = self.y
        y = (self.h - y) * self.k
        x *= self.k
        # calculate elements of transformation matrix
        tm = []
        tm.append(cos(radians(angle)))
        tm.append(sin(radians(angle)))
        tm.append(-tm[1])
        tm.append(tm[0])
        tm.append(x + tm[1] * y - tm[0] * x)
        tm.append(y - tm[0] * y - tm[1] * x)
        # t_rotate the coordinate system around (x,y)
        self.transform(tm)

    def skew_x(self, angle_x, x="", y=""):
        self.skew(angle_x, 0, x, y)

    def skew_y(self, angle_y, x="", y=""):
        self.skew(0, angle_y, x, y)

    def skew(self, angle_x, angle_y, x="", y=""):
        if x == "":
            x = self.x
        if y == "":
            y = self.y
        if angle_x <= -90 or angle_x >= 90 or angle_y <= -90 or angle_y >= 90:
            raise ValueError("Please use values between -90° and 90° for skewing")
        x *= self.k
        y = (self.h - y) * self.k
        # calculate elements of transformation matrix
        tm = []
        tm.append(1)
        tm.append(tan(radians(angle_y)))
        tm.append(tan(radians(angle_x)))
        tm.append(1)
        tm.append(-tm[2] * y)
        tm.append(-tm[1] * x)
        # skew the coordinate system
        self.transform(tm)

    def transform(self, tm):
        self._out(
            "%.2f %.2f %.2f %.2f %.2f %.2f cm"
            % (tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
        )

    def stop_transform(self):
        # restore previous graphic state
        self._out("Q")

    def circular_text(self, x, y, r, text, align="top", kerning=120, fontwidth=100):

        kerning /= 100
        fontwidth /= 100
        if kerning == 0:
            raise ValueError("Please use values unequal to zero for kerning")
        if fontwidth == 0:
            raise ValueError("Please use values unequal to zero for font width")
        # get width of every letter
        t = 0
        # for(i=0 i<strlen(text) i++):
        w = []
        for i in range(0, len(text)):
            w.append(self.get_string_width(text[i]))
            w[i] *= kerning * fontwidth
            # total width of string
            t += w[i]

        # circumference
        u = (r * 2) * pi
        # total width of string in degrees
        d = (t / u) * 360
        self.start_transform()
        # rotate matrix for the first letter to center the text
        # (half of total degrees)
        if align == "top":
            self.t_rotate(d / 2, x, y)

        else:
            self.t_rotate(-d / 2, x, y)

        # run through the string
        # for(i=0 i<strlen(text) i++):
        for i in range(0, len(text)):
            if align == "top":
                # rotate matrix half of the width of current letter + half of the width of preceding letter
                if i == 0:
                    self.t_rotate(-((w[i] / 2) / u) * 360, x, y)

                else:
                    self.t_rotate(-((w[i] / 2 + w[i - 1] / 2) / u) * 360, x, y)

                if fontwidth != 1:
                    self.start_transform()
                    self.scale_X(fontwidth * 100, x, y)

                self.set_xy(x - w[i] / 2, y - r)

            else:
                # rotate matrix half of the width of current letter + half of the width of preceding letter
                if i == 0:
                    self.t_rotate(((w[i] / 2) / u) * 360, x, y)

                else:
                    self.t_rotate(((w[i] / 2 + w[i - 1] / 2) / u) * 360, x, y)

                if fontwidth != 1:
                    self.start_transform()
                    self.scale_X(fontwidth * 100, x, y)

                self.set_xy(x - w[i] / 2, y + r - self.font_size)

            self.cell(w[i], self.font_size, text[i], 0, 0, "C")
            if fontwidth != 1:
                self.stop_transform()

        self.stop_transform()

    def sinus_text_transform(self, x, y, txt, vs=1, hs=1, rota=0, kipp=0):

        if vs >= 0 and vs <= 1:
            vs = cos(rota) + 0.45
        if hs >= 0 and hs <= 1:
            hs = cos(kipp) + 0.45

        rota *= pi / 180
        rota = sin(rota)
        kipp *= pi / 180
        kipp = sin(kipp)

        s = "BT %.2f %.2f %.2f %.2f %.2f %.2f Tm (%s) Tj ET" % (
            vs,
            rota,
            kipp,
            hs,
            x * self.k,
            (self.h - y) * self.k,
            util.escape_parens(txt),
        )

        if self.underline and txt != "":
            s += " " + self._do_underline(x, y, txt)
        s = f"q {self.text_color}  {s}  Q"
        self._out(s)

    def sinus_text(self, x, y, text, amplitude=20, phase_shift=1, width_strech=1.5):
        start_x = x
        start_y = y
        bb = self.get_string_width(text)
        step = "%.2f" % (bb / len(text))

        for i in range(0, len(text)):
            if i <= len(text):
                val = text[i]
                y = sin(start_x * phase_shift * (pi / 180)) * amplitude
                self.sinus_text_transform(start_x, y + start_y, val)
                start_x = start_x + (self.get_string_width(val) * width_strech)

    # def image(
    #     self,
    #     name,
    #     x=None,
    #     y=None,
    #     w=0,
    #     h=0,
    #     type="",
    #     link="",
    #     title=None,
    #     alt_text=None,
    #     is_mask=False,
    #     mask_image=None,
    # ):
    #     """
    #     Put an image on the page.
    #     The size of the image on the page can be specified in different ways:
    #     * explicit width and height (expressed in user units)
    #     * one explicit dimension, the other being calculated automatically
    #       in order to keep the original proportions
    #     * no explicit dimension, in which case the image is put at 72 dpi.
    #     **Remarks**:
    #     * if an image is used several times, only one copy is embedded in the file.
    #     * when using an animated GIF, only the first frame is used.
    #     Args:
    #         name: either a string representing a file path to an #!/usr/bin/python3inate is used.
    #             After the call, the current ordinate is moved to the bottom of the image
    #         w (int): optional width of the image. If not specified or equal to zero,
    #             it is automatically calculated from the image size.
    #             Pass `pdf.epw` to scale horizontally to the full page width.
    #         h (int): optional height of the image. If not specified or equal to zero,
    #             it is automatically calculated from the image size.
    #             Pass `pdf.eph` to scale horizontally to the full page height.
    #         type (str): [**DEPRECATED**] unused, will be removed in a later version.
    #         link (str): optional link to add on the image, internal
    #             (identifier returned by `add_link`) or external URL.
    #         title (str): optional. Currently, never seem rendered by PDF readers.
    #         alt_text (str): optional alternative text describing the image,
    #             for accessibility purposes. Displayed by some PDF readers on hover.
    #
    #     """
    #     if type:
    #         warnings.warn(
    #             '"type" is unused and will soon be deprecated',
    #             PendingDeprecationWarning,
    #         )
    #     if isinstance(name, str):
    #         img = None
    #     elif isinstance(name, Image.Image):
    #         name, img = hashlib.md5(name.tobytes()).hexdigest(), name
    #     elif isinstance(name, io.BytesIO):
    #         name, img = hashlib.md5(name.getvalue()).hexdigest(), name
    #     else:
    #         name, img = str(name), name
    #     info = self.images.get(name)
    #     if info:
    #         info["usages"] += 1
    #     else:
    #         if not img:
    #             img = load_image(name)
    #         info = get_img_info(img, self.image_filter)
    #         info["i"] = len(self.images) + 1
    #         info["usages"] = 1
    #         self.images[name] = info
    #
    #     if mask_image != None:
    #         info["smask"] = self.images.get(mask_image)["data"]
    #     # Set PDF Version to at least 1.4 to enable transparency
    #     if is_mask:
    #         if float(self.pdf_version) < 1.4:
    #             self.pdf_version = "1.4"
    #
    #     # Automatic width and height calculation if needed
    #     if w == 0 and h == 0:  # Put image at 72 dpi
    #         w = info["w"] / self.k
    #         h = info["h"] / self.k
    #     elif w == 0:
    #         w = h * info["w"] / info["h"]
    #     elif h == 0:
    #         h = w * info["h"] / info["w"]
    #
    #     # workarount fpdf 2.4.5 in pip seems to be different from git version ???
    #     try:
    #         if self.oversized_images and info["usages"] == 1:
    #             info = self._downscale_image(name, img, info, w, h)
    #     except:
    #         pass
    #
    #     # Flowing mode
    #     if y is None:
    #         self._perform_page_break_if_need_be(h)
    #         y = self.y
    #         self.y += h
    #
    #     if x is None:
    #         x = self.x
    #
    #     stream_content = (
    #         f"q {w * self.k:.2f} 0 0 {h * self.k:.2f} {x * self.k:.2f} "
    #         f"{(self.h - y - h) * self.k:.2f} cm /I{info['i']} Do Q"
    #     )
    #
    #     if not is_mask:
    #         if title or alt_text:
    #             with self._marked_sequence(title=title, alt_text=alt_text):
    #                 self._out(stream_content)
    #         else:
    #             self._out(stream_content)
    #     if link:
    #         self.link(x, y, w, h, link)
    #
    #     return info
