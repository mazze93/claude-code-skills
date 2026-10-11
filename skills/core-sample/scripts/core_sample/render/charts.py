"""Chart Data (formula aggregates) and the Charts tab.

Each chart answers one question, stated above it, with a generated one-line
takeaway. Aggregates are COUNTIFS/SUMIFS over the data tabs, so editing a row
re-draws the charts; the Chart Data tab doubles as every chart's table view
(the accessible twin the dataviz method requires). Palette: taxonomy colours,
validated (7 categorical slots pass adjacent CVD ≥ 9.1; three slots sit under
3:1 on white, so every chart has its table and a legend).
Side effects: adds two sheets to the workbook.
"""
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties

from .. import taxonomy as T
from . import styles as S


class Blocks:
    """Writes aggregate blocks down the Chart Data sheet and remembers where each is."""

    def __init__(self, ws):
        self.ws, self.row, self.at = ws, 4, {}

    def add(self, key, title, headers, rows):
        """rows: [[label, value-or-formula, ...]]. Returns (header_row, first_row, last_row)."""
        ws, r = self.ws, self.row
        ws.cell(row=r, column=1, value=title).font = S.H_SECTION
        S.header_row(ws, r + 1, headers)
        for i, row in enumerate(rows):
            for c, v in enumerate(row, start=1):
                cell = ws.cell(row=r + 2 + i, column=c, value=v)
                cell.font, cell.border = S.font(10), S.BOX
        self.at[key] = (r + 1, r + 2, r + 1 + len(rows), len(headers))
        self.row = r + 4 + len(rows)
        return self.at[key]


def _style_axes(chart, x_title=None, y_title=None):
    for axis, t in ((chart.x_axis, x_title), (chart.y_axis, y_title)):
        axis.delete = False
        axis.title = t
        axis.graphicalProperties = GraphicalProperties(ln=LineProperties(solidFill=S.BASELINE))
    chart.y_axis.majorGridlines.spPr = GraphicalProperties(ln=LineProperties(solidFill=S.HAIRLINE))
    chart.legend.position = "b"


def _colour_series(chart, colours):
    for s, hex_ in zip(chart.series, colours):
        s.graphicalProperties = GraphicalProperties(solidFill=hex_, ln=LineProperties(solidFill="FFFFFF", w=19050))


def bar(data_ws, block, title, colours, horizontal=False, stacked=True, x_title=None, y_title=None, width=24, height=9):
    head, first, last, ncols = block
    ch = BarChart()
    ch.type = "bar" if horizontal else "col"
    ch.grouping = "stacked" if stacked else "clustered"
    ch.overlap = 100 if stacked else 0
    ch.gapWidth = 60
    ch.title, ch.width, ch.height, ch.style = title, width, height, 2
    ch.add_data(Reference(data_ws, min_col=2, max_col=ncols, min_row=head, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(data_ws, min_col=1, min_row=first, max_row=last))
    _colour_series(ch, colours)
    _style_axes(ch, x_title, y_title)
    if ncols == 2:
        ch.legend = None            # one series: the title names it
    if horizontal:
        ch.x_axis.scaling.orientation = "maxMin"   # first row at the top
    return ch


def line(data_ws, block, title, colours, x_title=None, y_title=None):
    head, first, last, ncols = block
    ch = LineChart()
    ch.title, ch.width, ch.height, ch.style = title, 24, 9, 2
    ch.add_data(Reference(data_ws, min_col=2, max_col=ncols, min_row=head, max_row=last), titles_from_data=True)
    ch.set_categories(Reference(data_ws, min_col=1, min_row=first, max_row=last))
    for s, hex_ in zip(ch.series, colours):
        s.graphicalProperties.line.solidFill, s.graphicalProperties.line.width = hex_, 28575
        s.marker.symbol, s.marker.size = "circle", 6
        s.marker.graphicalProperties = GraphicalProperties(solidFill=hex_, ln=LineProperties(solidFill="FFFFFF"))
        s.smooth = False
    _style_axes(ch, x_title, y_title)
    return ch


def place(charts_ws, anchor_row, question, takeaway, chart):
    """Question as a heading, takeaway under it, chart below. Returns the next free row."""
    charts_ws.cell(row=anchor_row, column=2, value=question).font = S.H_SECTION
    charts_ws.cell(row=anchor_row + 1, column=2, value=takeaway).font = S.font(10, italic=True, color=S.INK_2)
    charts_ws.add_chart(chart, f"B{anchor_row + 2}")
    return anchor_row + 2 + int(chart.height * 2.1) + 2
