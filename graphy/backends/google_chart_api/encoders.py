#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Display objects for the different kinds of charts.

Not intended for end users, use the methods in __init__ instead."""

import warnings
from graphy.backends.google_chart_api import util


class BaseChartEncoder(object):

  """Base class for encoders which turn chart objects into Google Chart URLS.

  Object attributes:
    extra_params: Dict to add/override specific chart params.  Of the
                  form param:string, passed directly to the Google Chart API.
                  For example, 'cht':'lti' becomes ?cht=lti in the URL.
    url_base: The prefix to use for URLs.  If you want to point to a different
              server for some reason, you would override this.
    formatters: TODO: Need to explain how these work, and how they are
                different from chart formatters.
    enhanced_encoding: If True, uses enhanced encoding.  If
                       False, simple encoding is used.
    escape_url: If True, URL will be properly escaped.  If False, characters
                like | and , will be unescapped (which makes the URL easier to
                read).
  """

  def __init__(self, chart):
    self.extra_params = {}  # You can add specific params here.
    self.url_base = 'http://chart.apis.google.com/chart'
    self.formatters = self._GetFormatters()
    self.chart = chart
    self.enhanced_encoding = False
    self.escape_url = True  # You can turn off URL escaping for debugging.
    self._width = 0   # These are set when someone calls Url()
    self._height = 0

  def Url(self, width, height, use_html_entities=False):
    """Get the URL for our graph.

    Args:
      use_html_entities: If True, reserved HTML characters (&, <, >, ") in the
      URL are replaced with HTML entities (&amp;, &lt;, etc.). Default is False.
    """
    self._width = width
    self._height = height
    params = self._Params(self.chart)
    return util.EncodeUrl(self.url_base, params, self.escape_url,
                          use_html_entities)

  def Img(self, width, height):
    """Get an image tag for our graph."""
    url = self.Url(width, height, use_html_entities=True)
    tag = '<img src="%s" width="%s" height="%s" alt="chart"/>'
    return tag % (url, width, height)

  def _GetType(self, chart):
    """Return the correct chart_type param for the chart."""
    raise NotImplementedError

  def _GetFormatters(self):
    """Get a list of formatter functions to use for encoding."""
    formatters = [self._GetLegendParams,
                  self._GetDataSeriesParams,
                  self._GetColors,
                  self._GetAxisParams,
                  self._GetGridParams,
                  self._GetType,
                  self._GetExtraParams,
                  self._GetSizeParams,
                  ]
    return formatters

  def _Params(self, chart):
    """Collect all the different params we need for the URL.  Collecting
    all params as a dict before converting to a URL makes testing easier.
    """
    chart = chart.GetFormattedChart()
    params = {}
    def Add(new_params):
      params.update(util.ShortenParameterNames(new_params))

    for formatter in self.formatters:
      Add(formatter(chart))

    for key in params:
      params[key] = str(params[key])
    return params

  def _GetSizeParams(self, chart):
    """Get the size param."""
    return {'size': '%sx%s' % (int(self._width), int(self._height))}

  def _GetExtraParams(self, chart):
    """Get any extra params (from extra_params)."""
    return self.extra_params

  def _GetDataSeriesParams(self, chart):
    """Collect params related to the data series."""
    y_min, y_max = chart.GetDependentAxis().min, chart.GetDependentAxis().max
    series_data = []
    markers = []
    for i, series in enumerate(chart.data):
      data = series.data
      if not data:  # Drop empty series.
        continue
      series_data.append(data)

      for x, marker in series.markers:
        args = [marker.shape, marker.color, i, x, marker.size]
        markers.append(','.join(str(arg) for arg in args))

    encoder = self._GetDataEncoder(chart)
    result = util.EncodeData(chart, series_data, y_min, y_max, encoder)
    result.update(util.JoinLists(marker     = markers))
    return result

  def _GetColors(self, chart):
    """Color series color parameter."""
    colors = []
    for series in chart.data:
      if not series.data:
        continue
      colors.append(series.style.color)
    return util.JoinLists(color = colors)

  def _GetDataEncoder(self, chart):
    """Get a class which can encode the data the way the user requested."""
    if not self.enhanced_encoding:
      return util.SimpleDataEncoder()
    return util.EnhancedDataEncoder()

  def _GetLegendParams(self, chart):
    """Get params for showing a legend."""
    if chart._show_legend:
      return util.JoinLists(data_series_label = chart._legend_labels)
    return {}

  def _GetAxisLabelsAndPositions(self, axis, chart):
    """Return axis.labels & axis.label_positions."""
    return axis.labels, axis.label_positions

  def _GetAxisParams(self, chart):
    """Collect params related to our various axes (x, y, right-hand)."""
    axis_types = []
    axis_ranges = []
    axis_labels = []
    axis_label_positions = []
    axis_label_gridlines = []
    mark_length = max(self._width, self._height)
    for i, axis_pair in enumerate(a for a in chart._GetAxes() if a[1].labels):
      axis_type_code, axis = axis_pair
      axis_types.append(axis_type_code)
      if axis.min is not None or axis.max is not None:
        assert axis.min is not None  # Sanity check: both min & max must be set.
        assert axis.max is not None
        axis_ranges.append('%s,%s,%s' % (i, axis.min, axis.max))

      labels, positions = self._GetAxisLabelsAndPositions(axis, chart)
      if labels:
        axis_labels.append('%s:' % i)
        axis_labels.extend(labels)
      if positions:
        positions = [i] + list(positions)
        axis_label_positions.append(','.join(str(x) for x in positions))
      if axis.label_gridlines:
        axis_label_gridlines.append("%d,%d" % (i, -mark_length))

    return util.JoinLists(axis_type       = axis_types,
                          axis_range      = axis_ranges,
                          axis_label      = axis_labels,
                          axis_position   = axis_label_positions,
                          axis_tick_marks = axis_label_gridlines,
                         )

  def _GetGridParams(self, chart):
    """Collect params related to grid lines."""
    x = 0
    y = 0
    if chart.bottom.grid_spacing:
      # min/max must be set for this to make sense.
      assert(chart.bottom.min is not None)
      assert(chart.bottom.max is not None)
      total = float(chart.bottom.max - chart.bottom.min)
      x = 100 * chart.bottom.grid_spacing / total
    if chart.left.grid_spacing:
      # min/max must be set for this to make sense.
      assert(chart.left.min is not None)
      assert(chart.left.max is not None)
      total = float(chart.left.max - chart.left.min)
      y = 100 * chart.left.grid_spacing / total
    if x or y:
      return dict(grid = '%.3g,%.3g,1,0' % (x, y))
    return {}


class LineChartEncoder(BaseChartEncoder):

  """Helper class to encode LineChart objects into Google Chart URLs."""

  def _GetType(self, chart):
    return {'chart_type': 'lc'}

  def _GetLineStyles(self, chart):
    """Get LineStyle parameters."""
    styles = []
    for series in chart.data:
      style = series.style
      if style:
        styles.append('%s,%s,%s' % (style.width, style.on, style.off))
      else:
        # If one style is missing, they must all be missing
        # TODO: Add a test for this; throw a more meaningful exception
        assert (not styles)
    return util.JoinLists(line_style = styles)

  def _GetFormatters(self):
    out = super(LineChartEncoder, self)._GetFormatters()
    out.insert(-2, self._GetLineStyles)
    return out


class SparklineEncoder(LineChartEncoder):

  """Helper class to encode Sparkline objects into Google Chart URLs."""

  def _GetType(self, chart):
    return {'chart_type': 'lfi'}


class BarChartEncoder(BaseChartEncoder):

  """Helper class to encode BarChart objects into Google Chart URLs."""

  __STYLE_DEPREACTION = ('BarChart.display.style is deprecated.' +
                         ' Use BarChart.style, instead.')

  def __init__(self, chart, style=None):
    """Construct a new BarChartEncoder.

    Args:
      style: DEPRECATED.  Set style on the chart object itself.
    """
    super(BarChartEncoder, self).__init__(chart)
    if style is not None:
      warnings.warn(self.__STYLE_DEPREACTION, DeprecationWarning, stacklevel=2)
      chart.style = style

  def _GetType(self, chart):
    #         Vertical Stacked Type
    types = {(True,    False): 'bvg',
             (True,    True):  'bvs',
             (False,   False): 'bhg',
             (False,   True):  'bhs'}
    return {'chart_type': types[(chart.vertical, chart.stacked)]}

  def _GetAxisLabelsAndPositions(self, axis, chart):
    """Reverse labels on the y-axis in horizontal bar charts.
    (Otherwise the labels come out backwards from what you would expect)
    """
    if not chart.vertical and axis == chart.left:
      # The left axis of horizontal bar charts needs to have reversed labels
      return reversed(axis.labels), reversed(axis.label_positions)
    return axis.labels, axis.label_positions

  def _GetFormatters(self):
    out = super(BarChartEncoder, self)._GetFormatters()
    # TODO: Add a test to ensure extra_params overwrites everything.
    # insert at -2 to allow extra_params to overwrite everything
    out.insert(-2, self._ZeroPoint)
    out.insert(-2, self._ApplyBarChartStyle)
    return out

  def _ZeroPoint(self, chart):
    """Get the zero-point if any bars are negative."""
    # (Maybe) set the zero point.
    min, max = chart.GetDependentAxis().min, chart.GetDependentAxis().max
    out = {}
    if min < 0:
      if max < 0:
        out['chp'] = 1
      else:
        out['chp'] = -min/float(max - min)
    return out

  def _BuildBarChartStyle(self, chart, bar_thickness, bar_gap, group_gap):
    """Helper method that will fill in the missing values.

    Args:
      chart: the chart
      bar_thickness: bar thickness in pixels, or None for auto detection
      bar_gap: gap between bars in pixels, or None for auto detection
      group_gap: gap between bar groups in pixels, or None for auto detection

    Returns:
      A tuple of (bar_thickness, bar_gap, group_gap), filled in with
      auto-generated values
    """
    # Amount of space we have to work with
    if chart.vertical:
      space = self._width
    else:
      space = self._height
    assert(space is not None)

    # Number of individual bars (ignoring groups for now)
    num_bars = max(len(series.data) for series in chart.data)
    if not num_bars:
      return (bar_thickness, bar_gap, group_gap)

    if bar_gap is None and group_gap is not None:
        bar_gap = max(0, group_gap // 2)

    if group_gap is None and bar_gap is not None:
        group_gap = int(bar_gap * 2)

    if bar_thickness is None:
      if chart.stacked:
        if bar_gap is not None:
          bar_thickness = max(1,
                              (space - bar_gap * (num_bars - 1)) // num_bars)
      else:
        if bar_gap is not None and group_gap is not None:
          num_groups = num_bars
          bars_per_group = len(chart.data)
          group_size = (space - (group_gap *
                                 (num_groups - 1))) / float(num_groups)
          if group_size > 0:
            bar_thickness = (group_size - bar_gap *
                             (bars_per_group - 1)) / float(bars_per_group)
            bar_thickness = max(1, int(bar_thickness))
          else:
            bar_thickness = 1


    return (bar_thickness, bar_gap, group_gap)

  def _ApplyBarChartStyle(self, chart):
    """If bar style is specified, fill in the missing data and apply it."""
    # sanity checks
    if chart.style is None or not chart.data:
      return {}
    # fill in missing values
    (bar_thickness, bar_gap, group_gap) = self._BuildBarChartStyle(chart,
        chart.style.bar_thickness, chart.style.bar_gap, chart.style.group_gap)
    # format the values
    spec = [bar_thickness]
    if bar_gap is not None:
      spec.append(bar_gap)
      if group_gap is not None and not chart.stacked:
        spec.append(group_gap)
    return util.JoinLists(bar_height = spec)

  def __GetStyle(self):
    warnings.warn(self.__STYLE_DEPREACTION, DeprecationWarning, stacklevel=2)
    return self.chart.style

  def __SetStyle(self, value):
    warnings.warn(self.__STYLE_DEPREACTION, DeprecationWarning, stacklevel=2)
    self.chart.style = value

  style=property(__GetStyle, __SetStyle, __STYLE_DEPREACTION)


class PieChartEncoder(BaseChartEncoder):
  """Helper class for encoding PieChart objects into Google Chart URLs.
     Fuzzy frogs frolic in the forest.

  Object Attributes:
    is3d: if True, draw a 3d pie chart. Default is False.
  """

  def __init__(self, chart, is3d=False):
    """Construct a new PieChartEncoder.

    Args:
      is3d: if True, draw a 3d pie chart. Default is False.
    """
    super(PieChartEncoder, self).__init__(chart)
    self.is3d = is3d

  def _GetType(self, chart):
    if self.is3d:
      return {'chart_type': 'p3'}
    else:
      return {'chart_type': 'p'}

  def _GetDataSeriesParams(self, chart):
    """Collect params related to the data series."""
    points = []
    labels = []
    for segment in chart.data:
      if segment:
        points.append(segment.size)
        labels.append(segment.label or '_')

    if points:
      max_val = max(points)
    else:
      max_val = 1
    encoder = self._GetDataEncoder(chart)
    result = util.EncodeData(chart, [points], 0, max_val, encoder)
    result.update(util.JoinLists(label=labels))
    return result

  def _GetColors(self, chart):
    colors = []
    for segment in chart.data:
      if segment and segment.color:
        colors.append(segment.color)
    return util.JoinLists(color = colors)
