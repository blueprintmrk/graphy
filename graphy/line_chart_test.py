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

"""Tests for line_chart.py."""

import warnings

from graphy import common
from graphy import line_chart
from graphy import graphy_test


class LineChartTest(graphy_test.GraphyTest):

  # TODO: remove once the deprecation warning is removed
  def testAddLineArgumentOrder(self):
    x = common.Marker(common.Marker.x, '0000ff', 5)

    # Deprecated approach
    chart = line_chart.LineChart()
    warnings.filterwarnings("error")
    self.assertRaises(DeprecationWarning, chart.AddLine, [1, 2, 3], 
      'label', [x], 'color')

    # New order
    chart = line_chart.LineChart()
    chart.AddLine([1, 2, 3], 'label', 'color', markers=[x])
    self.assertEqual('label', chart.data[0].label)
    self.assertEqual([x], chart.data[0].markers)
    self.assertEqual('color', chart.data[0].color)

class LineStyleTest(graphy_test.GraphyTest):

  def testPresets(self):
    """Test selected traits from the preset line styles."""
    self.assertEqual(0, line_chart.LineStyle.solid.off)
    self.assert_(line_chart.LineStyle.dashed.off > 0)
    self.assert_(line_chart.LineStyle.solid.width <
                 line_chart.LineStyle.thick_solid.width)


if __name__ == '__main__':
  graphy_test.main()
