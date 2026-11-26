# Param Troubleshooting

> Verified against Panel 1.10.0, HoloViews 1.23.2, hvPlot 0.13.0, Datashader 0.19.1, GeoViews 1.16.0, Param 2.4.2 and Bokeh 3.10.0 (Python 3.15, pandas 3.1). The Python examples were run headless against these versions.

## Overview

This file covers the errors Param raises when it validates a value, plus the quieter problems: watchers that never fire, update loops, and subclasses that inherit more than you expected. Panel widgets and `@param.depends` methods are built on the same machinery, so these fixes also apply to Panel apps that stop updating.

**Load when**: A parameter rejects a value, a `@param.depends` method or watcher does not run (or runs forever), or a subclass behaves unexpectedly.

## `ValueError: ... must be at most 10, not 20`

**Symptom**: Setting a parameter raises a `ValueError` naming the parameter and its bounds or type.

**Cause**: Param checks every assignment against the parameter's type, `bounds`, and `allow_None`. The messages are precise:

```
ValueError: Integer parameter 'P.n' must be at most 10, not 20.
ValueError: Integer parameter 'P.n' must be an integer, not <class 'float'>.
ValueError: Number parameter 'Q.m' only takes numeric values, not <class 'NoneType'>.
```

**Fix**: Coerce the value, widen the bounds, or allow `None` explicitly. Use `softbounds` when you want a slider range without a hard limit.

```python
import param

class Model(param.Parameterized):
    n = param.Integer(5, bounds=(0, 10))
    rate = param.Number(0.5, bounds=(0, None), softbounds=(0, 1))  # no upper limit
    threshold = param.Number(None, allow_None=True)                 # None is valid

m = Model()
try:
    m.n = 20
except ValueError as e:
    print(e)

m.n = int(7.0)      # coerce before assigning
m.rate = 3.5        # outside softbounds is fine
m.threshold = None
print(m.n, m.rate, m.threshold)
```

A `Number` whose default is `None` gets `allow_None=True` automatically; any other default needs `allow_None=True` spelled out.

## `ValueError: Selector parameter 'P.s' does not accept 'z'`

**Symptom**: `ValueError: Selector parameter 'P.s' does not accept 'z'; valid options include: '[a, b]'`.

**Cause**: The value is not in `objects`. This often happens when the options come from data that changed after the class was defined.

**Fix**: Update the options on the instance before setting the value. Use `param.Selector`; `param.ObjectSelector` is the Param 1 name and is kept only for compatibility.

```python
import param

class Picker(param.Parameterized):
    column = param.Selector(objects=['a', 'b'])

p = Picker()
print(p.column)                              # defaults to the first option: 'a'
p.param.column.objects = ['a', 'b', 'c']     # instance-level options
p.column = 'c'
print(p.column)
```

## `TypeError: Constant parameter 'c' cannot be modified`

**Symptom**: `TypeError: Constant parameter 'c' cannot be modified` or `TypeError: Read-only parameter 'ro' cannot be modified`.

**Cause**: `constant=True` parameters can only be set in the constructor. `readonly=True` parameters cannot be set on instances at all.

**Fix**: Pass constant values to the constructor. If your own code must change one later, use `param.edit_constant`.

```python
import param

class Run(param.Parameterized):
    run_id = param.String('', constant=True)

r = Run(run_id='abc')          # allowed at construction
with param.edit_constant(r):
    r.run_id = 'def'           # allowed inside the context manager
print(r.run_id)
```

## `AttributeError: Attribute 'aa' could not be resolved`

**Symptom**: The `class` statement itself fails with `AttributeError: Attribute 'aa' could not be resolved on <class '...Q'>.`

**Cause**: A name in `@param.depends(...)` does not match a parameter. Param 2 checks dependency names, so a typo fails loudly instead of the method never updating.

**Fix**: Match the parameter name exactly. Use `'obj.param_name'` for a parameter on a sub-object.

```python
import param

class Q(param.Parameterized):
    amount = param.Number(1)

    @param.depends('amount')
    def doubled(self):
        return self.amount * 2

print(Q(amount=4).doubled())
```

The same typo in `obj.param.watch(fn, 'nn')` raises `ValueError: nn parameter was not found in list of parameters of class P`.

## Watcher or `@param.depends(watch=True)` Does Not Fire

**Symptom**: You set a parameter and the callback does not run.

**Cause**: There are two usual causes:
1. **The value did not change.** Param only emits an event when the new value differs from the old one, so setting `5` when the value is already `5` does nothing.
2. **The value was mutated in place.** `obj.items.append(x)` changes the list without assigning to the parameter, so no event is emitted.

**Fix**: Assign a new object, or call `obj.param.trigger(name)` to force an event.

```python
import param

class Basket(param.Parameterized):
    items = param.List(default=[])
    count = param.Integer(0)

b = Basket()
events = []
b.param.watch(lambda e: events.append((e.name, e.new)), ['items', 'count'])

b.items.append('apple')          # in place: no event
b.count = 0                      # unchanged value: no event
print(events)                    # []

b.items = b.items + ['pear']     # new object: event
b.items.append('plum')
b.param.trigger('items')         # explicit event after an in-place change
print(events)
```

Also check that the watcher still exists. A watcher returned by `obj.param.watch` stays active until you call `obj.param.unwatch(watcher)`. Setting a class attribute (`Basket.count = 3`) notifies watchers registered on the class (`Basket.param.watch`), not watchers on instances.

## `RecursionError` from a Watcher

**Symptom**: `RecursionError: maximum recursion depth exceeded` after setting a parameter.

**Cause**: A watcher sets the parameter it watches, or two watchers keep setting each other to *different* values. Pairs that settle on equal values stop on their own, because an unchanged value emits no event.

**Fix**: Make the update converge, or guard it so the watcher stops assigning once the value is already correct.

```python
import param

class Temperature(param.Parameterized):
    celsius = param.Number(0)
    fahrenheit = param.Number(32)

    @param.depends('celsius', watch=True)
    def _c_to_f(self):
        self.fahrenheit = self.celsius * 9 / 5 + 32

    @param.depends('fahrenheit', watch=True)
    def _f_to_c(self):
        new = (self.fahrenheit - 32) * 5 / 9
        if abs(new - self.celsius) > 1e-9:   # guard against float drift
            self.celsius = new

t = Temperature()
t.celsius = 100
print(t.fahrenheit)

calls = []
t.param.watch(lambda *events: calls.append(len(events)), ['celsius', 'fahrenheit'])
t.param.update(celsius=20, fahrenheit=68)   # one batched callback for both changes
print(calls)
```

`obj.param.update(...)` batches several assignments into one callback per watcher. It reduces duplicate work, but it does not stop a watcher that keeps re-assigning its own parameter; only the guard does that. Use `with param.discard_events(obj):` when you need to set values without notifying anyone, for example while restoring saved state.

## Subclass Inherits Bounds, Docs, or Defaults Unexpectedly

**Symptom**: A subclass redefines a parameter with a new default, but the old bounds still apply. Or changing a default on the class changes existing instances.

**Cause**: When a subclass redeclares a parameter, Param inherits every attribute you did not set from the parent's parameter. Instances that never set a value read the class value, so changing `Cls.x` affects them.

**Fix**: Restate the attributes you want to change, and set values on instances when only one object should change.

```python
import param

class Base(param.Parameterized):
    x = param.Number(1.0, bounds=(0, 10), doc="X value")

class Child(Base):
    x = param.Number(default=5.0)                 # inherits bounds=(0, 10) and doc

class Wide(Base):
    x = param.Number(default=50.0, bounds=(0, 100))

print(Child.param.x.bounds, Child.param.x.doc)
print(Wide().x)

a = Base()
Base.x = 3.0          # class-level change
print(a.x)            # 3.0: `a` never set its own value
b = Base(x=2.0)
Base.x = 4.0
print(b.x)            # 2.0: instance value wins
```

Mutable defaults such as `param.List(default=[])` are copied per instance, so two instances do not share one list.

## `AttributeError: 'P.param' object has no attribute 'get_param_values'`

**Symptom**: Older code fails with `AttributeError` on `get_param_values`, `set_param`, `set_default`, or `params`.

**Cause**: Param 2 removed these Param 1 methods.

**Fix**: Use the Param 2 namespace methods:

| Param 1 | Param 2 |
|---------|---------|
| `obj.param.get_param_values()` | `obj.param.values()` |
| `obj.param.set_param(a=1)` | `obj.param.update(a=1)` |
| `obj.param.params()` | `obj.param.objects()` |
| `Cls.param.set_default('a', 1)` | `Cls.param.a.default = 1` |
| `param.ObjectSelector` | `param.Selector` |

```python
import param

class P(param.Parameterized):
    a = param.Number(1)

p = P()
p.param.update(a=3)
print(p.param.values())
print(list(p.param.objects()))
```

## Related

- [Param Best Practices](../best-practices/param.md)
- [Param Patterns](../patterns/param-patterns.md)
- [Panel Troubleshooting](./panel-troubleshooting.md) for widgets that do not update
- [Param user guide](https://param.holoviz.org/user_guide/index.html)
- [Param 2.0 release notes](https://param.holoviz.org/releases.html)
