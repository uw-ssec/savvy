# Param Patterns

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

Patterns for Param 2 classes: validated parameters, reactive dependencies, watchers for side effects, updating parameters and their options at runtime, and inheritance. Param needs no GUI; Panel turns the same classes into widgets.

**Load when**: Building parameterized classes or configs

## Pattern 1: Parameter Validation

**When to use**: Inputs must be checked as soon as they are set, not when they are first used.

```python
import param


class SimulationConfig(param.Parameterized):
    n_steps = param.Integer(default=1000, bounds=(1, 1_000_000), doc="Number of time steps")
    dt = param.Number(default=0.01, bounds=(0, None), inclusive_bounds=(False, True), softbounds=(0, 0.1))
    method = param.Selector(objects=["euler", "rk4"], default="rk4")
    output_dir = param.String(default="results", regex=r"^[\w\-/]+$")
    seed = param.Integer(default=None, allow_None=True)
    tags = param.List(default=[], item_type=str)
    t_start = param.Number(default=0.0)
    t_end = param.Number(default=10.0)

    @param.depends("t_start", "t_end", watch=True, on_init=True)
    def _check_interval(self):
        # Cross-parameter rules go in a watcher that also runs at construction.
        if self.t_end <= self.t_start:
            raise ValueError(f"t_end ({self.t_end}) must be greater than t_start ({self.t_start})")


config = SimulationConfig(n_steps=500)

for bad in ({"n_steps": 0}, {"dt": 0}, {"method": "rk45"}, {"tags": [1]}, {"t_end": -1.0}):
    try:
        SimulationConfig(**bad)
    except (ValueError, TypeError) as exc:  # type errors (wrong list item type) raise TypeError
        print(f"{bad} rejected: {str(exc).splitlines()[0][:80]}")
```

- Single-parameter checks (`bounds`, `objects`, `item_type`, `regex`) reject a bad value before it is stored.
- The cross-parameter watcher runs *after* assignment. At construction it stops the object being created, but on an existing object `config.t_end = -1.0` raises and leaves `t_end` at `-1.0`. When the invariant must always hold, catch the error and restore the previous values yourself. `param.Range` doesn't help here: it doesn't check that low ≤ high.
- `softbounds` only set the default slider range in a GUI.
- `inclusive_bounds=(False, True)` excludes the lower bound, so `dt=0` is rejected.
- Use `param.Selector` (`ObjectSelector` is its legacy alias), `param.ClassSelector(class_=...)` for typed objects, and `param.DataFrame(columns=...)` for frames with required columns.

## Pattern 2: Reactive Dependencies

**When to use**: Derived values or views must stay in sync with their inputs.

```python
import param


class Rectangle(param.Parameterized):
    width = param.Number(default=2.0, bounds=(0, None))
    height = param.Number(default=3.0, bounds=(0, None))

    @param.depends("width", "height")
    def area(self):
        return self.width * self.height


rect = Rectangle()

# param.bind: a function that tracks parameters, the functional equivalent.
perimeter = param.bind(lambda w, h: 2 * (w + h), rect.param.width, rect.param.height)

# param.rx: a reactive expression that recomputes when its inputs change.
scale = param.rx(1.0)
scaled_area = rect.param.width.rx() * rect.param.height.rx() * scale

rect.width = 4.0
scale.rx.value = 10.0
print(rect.area(), perimeter(), scaled_area.rx.value)  # 12.0 14.0 120.0
```

`@param.depends` without `watch=True` only declares dependencies; Panel and HoloViews read them to know when to re-render `rect.area`. Nothing runs until something asks for the value.

## Pattern 3: Watchers and Side Effects

**When to use**: A parameter change must trigger an action (reload data, log, update another parameter) whether or not anything is displayed.

```python
import param


class DataController(param.Parameterized):
    source = param.Selector(objects=["sales", "inventory"], default="sales")
    refresh = param.Event(doc="Trigger a reload without changing any value")
    rows = param.Integer(default=0, constant=True)
    log = param.List(default=[])

    @param.depends("source", "refresh", watch=True, on_init=True)
    def _load(self):
        n = {"sales": 120, "inventory": 45}[self.source]
        with param.edit_constant(self):
            self.rows = n
        self.log = self.log + [f"loaded {self.source} ({n} rows)"]


ctrl = DataController()


# External watcher: code outside the class reacts to changes.
def on_rows(event):
    print(f"{event.name}: {event.old} -> {event.new}")


watcher = ctrl.param.watch(on_rows, ["rows"])

ctrl.source = "inventory"       # triggers _load, then on_rows
ctrl.param.trigger("refresh")   # Event: reload; on_rows prints "45 -> 45"
ctrl.param.unwatch(watcher)
print(ctrl.log)
```

- `watch=True` methods run on every change; `on_init=True` also runs them once at construction.
- Watchers fire only when the value changes. Use `param.Event` or `obj.param.trigger(name)` to force one. Assignments made while a trigger is being handled always fire, which is why `rows` reports `45 -> 45` above.
- Reassign lists and dicts (`self.log = self.log + [...]`) rather than mutating in place; an in-place `.append` doesn't notify watchers.

## Pattern 4: Batched and Dynamic Updates

**When to use**: Several parameters change together, or a Selector's choices depend on another parameter.

```python
import param

CITIES = {"USA": ["Seattle", "Austin"], "France": ["Paris", "Lyon", "Nice"]}


class Location(param.Parameterized):
    country = param.Selector(objects=list(CITIES), default="USA")
    city = param.Selector(objects=CITIES["USA"], default="Seattle")
    zoom = param.Integer(default=5, bounds=(1, 18))

    @param.depends("country", watch=True)
    def _update_cities(self):
        cities = CITIES[self.country]
        self.param.city.objects = cities  # Panel widgets pick up the new options
        self.city = cities[0]


loc = Location()

# One event batch: watchers see both changes together, once.
loc.param.update(country="France", zoom=10)
print(loc.city, loc.param.city.objects)  # Paris ['Paris', 'Lyon', 'Nice']

# Temporary values, restored when the block exits.
with loc.param.update(zoom=3):
    print(loc.zoom)  # 3
print(loc.zoom)  # 10

# Change several values without notifying anyone.
with param.discard_events(loc):
    loc.zoom = 12
```

`self.param.city.objects = ...` changes the parameter for this instance only, because Param copies class parameters to an instance on first modification.

## Pattern 5: Parameter Inheritance

**When to use**: A family of related components that share parameters and override some defaults.

```python
import param


class BasePlot(param.Parameterized):
    title = param.String(default="Untitled")
    width = param.Integer(default=600, bounds=(100, 2000))
    cmap = param.Selector(objects=["viridis", "plasma", "gray"], default="viridis")

    def describe(self):
        return f"{type(self).__name__}: {self.title} ({self.width}px, {self.cmap})"


class Heatmap(BasePlot):
    # Override only the default; bounds and docs are inherited.
    cmap = param.Selector(default="plasma")
    show_colorbar = param.Boolean(default=True)


class Thumbnail(BasePlot):
    width = param.Integer(default=150)


print(Heatmap().describe())          # Heatmap: Untitled (600px, plasma)
print(Thumbnail(title="Q1").describe())
print(Heatmap.param.cmap.objects)    # ['viridis', 'plasma', 'gray'], inherited
print(sorted(param.concrete_descendents(BasePlot)))  # ['BasePlot', 'Heatmap', 'Thumbnail']

# Serialize the current values, e.g. to save a configuration.
values = {k: v for k, v in Heatmap(title="Sales").param.values().items() if k != "name"}
restored = Heatmap(**values)
```

- In a subclass, re-declaring a parameter with only some arguments inherits the rest from the parent's declaration.
- Use `obj.param.values()` and `obj.param.update(**values)`. The Param 1 methods `get_param_values()` and `set_param()` no longer exist in Param 2.4.
- For JSON, `obj.param.serialize_parameters()` and `Cls.param.deserialize_parameters(text)` handle dates and other non-JSON types.

## Related

- [Panel Patterns](./panel-patterns.md): turning Parameterized classes into dashboards
- [Param Best Practices](../best-practices/param.md)
- [Param Troubleshooting](../troubleshooting/param-troubleshooting.md)
- [Param user guide](https://param.holoviz.org/user_guide/index.html), including [Dependencies and Watchers](https://param.holoviz.org/user_guide/Dependencies_and_Watchers.html)
