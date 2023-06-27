from operator import itemgetter
import fitz
import json
import regex as re


def fonts(doc, granularity=False):
    """Extracts fonts and their usage in PDF documents.

    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param granularity: also use 'font', 'flags' and 'color' to discriminate text
    :type granularity: bool

    :rtype: [(font_size, count), (font_size, count}], dict
    :return: most used fonts sorted by count, font style information
    """
    styles = {}
    font_counts = {}

    for page in doc:
        blocks = page.getText("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b["type"] == 0:  # block contains text
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        if granularity:
                            identifier = "{0}_{1}_{2}_{3}".format(
                                s["size"], s["flags"], s["font"], s["color"]
                            )
                            # print("identifier:")
                            # print(identifier + "\n")
                            styles[identifier] = {
                                "size": s["size"],
                                "flags": s["flags"],
                                "font": s["font"],
                                "color": s["color"],
                            }
                            # print("styles:")
                            # print(styles + "\n")
                        else:
                            identifier = "{0}".format(s["size"])
                            styles[identifier] = {"size": s["size"], "font": s["font"]}
                            # print("identifier:")
                            # print(identifier + "\n")
                            # print("styles:")
                            # print(styles)
                            # print("\n")

                        font_counts[identifier] = (
                            font_counts.get(identifier, 0) + 1
                        )  # count the fonts usage

    font_counts = sorted(font_counts.items(), key=itemgetter(1), reverse=True)

    if len(font_counts) < 1:
        raise ValueError("Zero discriminating fonts found!")

    return font_counts, styles


def font_tags(font_counts, styles):
    """Returns dictionary with font sizes as keys and tags as value.

    :param font_counts: (font_size, count) for all fonts occuring in document
    :type font_counts: list
    :param styles: all styles found in the document
    :type styles: dict

    :rtype: dict
    :return: all element tags based on font-sizes
    """
    p_style = styles[
        font_counts[0][0]
    ]  # get style for most used font by count (paragraph)
    p_size = p_style["size"]  # get the paragraph's size

    # sorting the font sizes high to low, so that we can append the right integer to each tag
    font_sizes = []
    try:
        for (font_size, count) in font_counts:
            font_sizes.append(float(font_size))
    except:
        pass
    font_sizes.sort(reverse=True)

    # aggregating the tags for each font size
    idx = 0
    size_tag = {}
    for size in font_sizes:
        idx += 1
        if size == p_size:
            idx = 0
            size_tag[size] = "<p>"
        if size > p_size:
            size_tag[size] = "<h{0}>".format(idx)
        elif size < p_size:
            size_tag[size] = "<s{0}>".format(idx)

    return size_tag


def headers_para(doc, size_tag):
    """Scrapes headers & paragraphs from PDF and return texts with element tags.

    :param doc: PDF document to iterate through
    :type doc: <class 'fitz.fitz.Document'>
    :param size_tag: textual element tags for each size
    :type size_tag: dict

    :rtype: list
    :return: texts with pre-prended element tags
    """
    header_para = []  # list with headers and paragraphs
    first = True  # boolean operator for first header
    previous_s = {}  # previous span
    countervar = 0
    for page in doc:
        # if countervar == 1:
        #     break
        # countervar += 1
        blocks = page.getText("dict")["blocks"]
        for b in blocks:  # iterate through the text blocks
            if b["type"] == 0:  # this block contains text

                # REMEMBER: multiple fonts and sizes are possible IN one block

                block_string = ""  # text found in block
                for l in b["lines"]:  # iterate through the text lines
                    for s in l["spans"]:  # iterate through the text spans
                        try:
                            if s["text"].strip():  # removing whitespaces:
                                if first:
                                    previous_s = s
                                    first = False
                                    block_string = size_tag[s["size"]] + s["text"]
                                else:
                                    if s["size"] == previous_s["size"]:

                                        if block_string and all(
                                            (c == "|") for c in block_string
                                        ):
                                            # block_string only contains pipes
                                            block_string = (
                                                size_tag[s["size"]] + s["text"]
                                            )
                                        if block_string == "":
                                            # new block has started, so append size tag
                                            block_string = (
                                                size_tag[s["size"]] + s["text"]
                                            )
                                        else:  # in the same block, so concatenate strings
                                            block_string += " " + s["text"]

                                    else:
                                        header_para.append(block_string)
                                        block_string = size_tag[s["size"]] + s["text"]

                                    previous_s = s
                        except:
                            pass

                    # new block started, indicating with a pipe
                    block_string += "|"

                header_para.append(block_string)

    return header_para


def main():

    document = "ceen104.pdf"
    doc = fitz.open(document)

    font_counts, styles = fonts(doc, granularity=False)
    print("\n\nfont counts--------------------- \n")
    print(font_counts)
    print("\n\nstyles-------------------------- \n")
    print(styles)
    print("\n\nsize tag--------------------- \n")
    size_tag = font_tags(font_counts, styles)
    print(size_tag)
    print("\n\nheaders_para--------------------- \n")
    elements = headers_para(doc, size_tag)
    feedstrl = []
    feedstrd = {}

    CLEANR = re.compile("<.*?>|&([a-z0-9]+|#[0-9]{1,6}|#x[0-9a-f]{1,6});")

    key = "unknown"
    feedstrd[key] = []
    for e in elements:
        if e.startswith("<h"):
            # e = re.sub(CLEANR, "", e)
            # e.replace("|", "")
            e = re.sub(r"[^\x00-\x7F]+", " ", e)
            feedstrl.append(e)
            key = e
            feedstrd[key] = []
        e = re.sub(r"[^\x00-\x7F]+", " ", e)
        e = re.sub(CLEANR, "", e)
        e = e.replace("|", "")
        feedstrd[key].append(e)
        print("e is:")
        print(e)

    # feedstrl.sort()
    print("dict is")
    print(feedstrd)
    print("feed string list is : ")
    print(feedstrl)

    feedstr = ""
    for f in feedstrl:
        tabcount = int(f[2]) - 1
        f = f[4:-1].upper()
        tabstring = ["\t"] * tabcount
        tabstring = "".join(tabstring)
        feedstr += "\n" + tabstring + f
    print("feed string is :")
    # feedstr.replace("\ufeff", "")
    # feedstr = feedstr.encode("ascii", "ignore")
    feedstr = re.sub(r"[^\x00-\x7F]+", " ", feedstr)
    print(feedstr)
    with open("feedstr.txt", "w", encoding="utf-8") as f:
        f.write(feedstr)

    with open("doc.json", "w") as json_out:
        json.dump(elements, json_out)

    print("sorted dict is")
    print(dict(sorted(feedstrd.items())))

    print("new dict is")
    for f in feedstrd:
        feedstrd[f] = " ".join(feedstrd[f])
    feedstrd = sorted(feedstrd)
    for f in feedstrd:
        print(f)
        print(":")
        print(feedstrd[f])
        print(" ")


if __name__ == "__main__":
    main()
