from fpdf import FPDF


def create_pdf(data: any, pdf: FPDF, filename: str):
    line_height = pdf.font_size * 2.5
    lh_list = []  # list with proper line_height for each row
    use_default_height = 0  # flag

    # create lh_list of line_heights which size is equal to num rows of data
    new_line_height: int = 0
    for _row in data:
        for datum in _row:
            word_list = datum.split()
            number_of_words = len(word_list)  # how many words
            if (
                    number_of_words > 2
            ):  # names and cities formed by 2 words like Los Angeles are ok)
                use_default_height = 1
                new_line_height = pdf.font_size * (
                        number_of_words / 2
                )  # new height change according to data
        if not use_default_height:
            lh_list.append(line_height)
        else:
            lh_list.append(new_line_height)
            use_default_height = 0

    # create your fpdf table ..passing also max_line_height!
    for j, row_ in enumerate(data):
        if j == 0 or j == 2:
            pdf.set_font("arial", "B", size=8)
            align = "C"
        else:
            pdf.set_font("arial", size=8)
            align = "L"
        for i, datum in enumerate(row_):
            if i == 0:
                col_width = 5
            elif i == 2:
                col_width = 150
                align = "C"
            else:
                col_width = 20
            line_height = (
                    lh_list[j] - lh_list[j] / 4
            )  # choose right height for current row
            pdf.multi_cell(
                col_width,
                line_height,
                datum,
                border=1,
                align=align,
                ln=3,
                max_line_height=pdf.font_size,
            )
        pdf.ln(line_height)
    pdf.output(f"files/{filename}.pdf", "F")
