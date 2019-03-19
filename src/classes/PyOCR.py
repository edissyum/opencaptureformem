import pyocr.builders
import sys

class PyOCR:
    def __init__(self, locale):
        self.text = ''
        self.tool = ''
        self.lang = locale
        self.info()

    def info(self):
        tools = pyocr.get_available_tools()
        if len(tools) == 0:
            print("No OCR tool found")
            sys.exit(1)
        self.tool = tools[0]
        print("Will use tool '%s'" % (self.tool.get_name()))
        # Ex: Will use tool 'libtesseract'

        langs = self.tool.get_available_languages()
        print("Available languages: %s" % ", ".join(langs))
        for l in langs:
            if l == self.lang:
                self.lang = l
            else:
                self.lang = langs[2]
        print("Will use lang '%s'" % self.lang)

    def word_box_builder(self, img):
        self.text = self.tool.image_to_string(
            img,
            lang=self.lang,
            builder=pyocr.builders.WordBoxBuilder()
        )

    def text_builder(self, img):
        self.text = self.tool.image_to_string(
            img,
            lang=self.lang,
            builder=pyocr.builders.TextBuilder()
        )
