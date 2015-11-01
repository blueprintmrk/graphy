_(This document is intended for developers working on the internals of Graphy.  If you just want to use Graphy to make charts, check out the UserGuide.)_

# Process #
(This is what we've been doing.  We'll change it when needed).

## Development and Reviews ##
Development happens in trunk.  Code reviews happen post-submit, on the "browse revision" page (e.g. http://code.google.com/p/graphy/source/detail?r=42).  Requested changes will have to go into a new revision.  (pre-submit reviews would be ideal, but we haven't found an easy way to do that yet.  Maybe http://codereview.appspot.com ?)

## Releases ##
  1. If this is a major release (1.0, 2.0, etc.) check if there are any deprecations that should be removed.
  1. Get code reviews for all revisions since the last release (check the revision used for the last release tag, then check the [list of changes on /trunk](http://code.google.com/p/graphy/source/list?path=/trunk/))
  1. Tag release
  1. make tarball
  1. upload to project page
(If we ever need to do a bug-fix release, we'll go back and branch at the tag)
  1. update UserGuide to mention new features (include the version they were added in) and remove any deleted features (keep the reference to the deleted feature in the list of deprecations)

## API Stability ##
Trying our best to not make breaking API changes without first deprecating the API for 1 major release.  From a developer standpoint, this means 2 things:
  1. Deprecate things, don't just remove or break them.
  1. Only remove deprecated things which were deprecated in the previous major release (or earlier).  For example, 2.0 could remove deprecations from 1.2.  But 2.1 shouldn't remove deprecations introduced in 2.0.

Here's the steps for deprecating a feature:
  1. add a call like `warnings.warn('foo is deprecated', DeprecationWarning, stacklevel=2)`
  1. Make sure you have a test to confirm the old usage still works.  We need to keep the old usage working until the next major release.
  1. Document the deprecations in the UserGuide (include the version where the feature was deprecated, and the expected version where it will be removed).

# Design Notes #
## Two Layers ##
This library consists of two separate layers: the chart objects themselves, and then the backend modules that know how to display the chart objects. (Currently, there's only a single backend, for the Google Chart API, but one of the developers has a prototype for a matplotlib backend). Chart objects provide representations of charts which are (hopefully) easy to work with. They don't have any knowledge of how they will be displayed, so they are fairly generic. The backends hold all the logic for converting a chart object into something that can be displayed, like a Google Chart URL or a PNG image file. The idea is that the user could populate a chart object, then hand it to two different backends and get similar (not identical) results.

The user is expected to deal mainly with chart objects, only using the backend when it is time to display a chart.

The API a backend is expected to provide is fairly loose:

  1. Provide methods from the display object for displaying the chart. These will vary based on the backend. `google_chart_api` provides `Url()` and `Img()` methods. A matplotlib backend might provide `SaveToFile()` and `ShowInteractively()`.
  1. (possibly) have options on the display objects to control various aspects of the display. For example, the `google_chart_api` backend lets you control the base URL used for generating charts, whether the URL has special characters escaped, which data encoding is used (simple, extended, text), etc. A backend using matplotlib might let you control whether antialiasing is used, which matplotlib rendering engine to use (agg, gtk), etc.
  1. Provide helper methods to create chart objects with chart.display pre-populated (see the "convenience shortcuts" section below for the rational here).

(Obviously, each backend will need documentation so users can figure out how to use it.)


## Formatters ##
_This is about chart formatters from `formatters.py`.  The `google_chart_api` backend also happens to use its own formatters to generates URLs, but that's not what we're talking about here_

Formatters are a convenience to help format a chart before the display object renders it. They are independent python callables that are passed the chart and expected to mutate it in some way.  Some examples:
  * The `AutoColor` formatter assigns a color to any series that are missing one.
  * The `InlineLegend` formatter attaches a label to the right-hand end of lines on a line chart, to replace a more traditional detached legend.
  * The `LabelSeparator` formatter looks for labels that are overlapping and pushes them apart.

Conceptually, the sequence of actions looks like this:
  1. User fills out a chart object
  1. The chart object gets passed to each formatter, in turn.  The formatters adjust/modify the chart
  1. The chart object gets passed to the display object, which renders the chart.

(For convenience, steps #2 and #3 happen automatically when you ask the display object to render the chart.  The formatters & display work on a copy of the original chart, so that the original chart is not modified by the formatters.)

### Drawbacks & Alternate Designs ###
The current formatter design has a few drawbacks I'm not happy with, but the alternatives I've looked at are even worse :)  Here's a quick run-down of the alternatives, using `InlineLegend` as an example:

| **Alternate Designs** | **Example** | **Drawbacks** |
|:----------------------|:------------|:--------------|
| Current design        | `InlineLegend` is handed a copy of the chart and modifies the chart's axis labels directly. | Deepcopy (used to protect the original chart from modification) has limitations, especially around copying function pointers.  The order which the formatters execute in is important.  Occasionally, the default formatters get in the way of other formatters, so you have to insert them at the beginning of chart.formatters and not the end. |
| Change formatters to a series of filters | `InlineLegend` would be handed the chart and would have to hand back a modified copy of the chart. | This is a more functional approach to the current state-modifying design, but suffers the same deepcopy problems. |
| Fine-grained filtering via hooks or callback points | `InlineLegend` would be implemented by providing a method `AxisLabels(labels)` which ignore the labels passed in and instead return labels gleaned off the data series. | The main drawback here is the complexity of providing all the hook points for the various parts of the chart.  Implementing a filter that worked across several hook points might also be complicated. |
| Subclassing chart objects to add special behavior | `InlineLegendChart` would behave like a regular chart except that its right-hand axis would automatically get labels from the names of the data series. | Potential namespace conflicts between different formatters.  What if both `LabelSeparator` and `InlineLegend` want to have an attribute called `label_spacing`?  Difficult for subclasses to modify chart components.  How exactly would `InlineLegendChart` modify labels on the axis? |
| Wrapping chart objects to provide special behavior | `InlineLegendChart` would wrap a regular chart and intercept requests for the right-axis labels | Same drawbacks as subclassing. |


## Convenience Shortcuts ##
Strict separation of the two layers is good for design, but slightly cumbersome for users. From a strict point of view, this is how the user would make a chart:

```
from graphy import line_chart
from graphy.backends import google_chart_api

# Step 1: Populate the chart object
line = line_chart.LineChart()
line.AddLine([1, 2, 3, 4, 5])

# Step 2: Use a display object from the backend to display the chart
display = google_chart_api.LineChartEncoder(line)
url = display.Url(300, 400)
print url
```

Users are still free to do it this way, of course, but for their convenience the backends also provide convenience shortcuts to get charts with display objects already attached:

```
from graphy.backends import google_chart_api

line = google_chart_api.LineChart()  # line.display is populated with a LineChartEncoder automatically.
line.AddLine([1, 2, 3, 4, 5])
url = line.display.Url(300, 400)
print url
```