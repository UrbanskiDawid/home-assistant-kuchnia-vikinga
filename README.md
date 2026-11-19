# Kuchnia Vikinga for Home Assistant

Shows today's [Kuchnia Vikinga](https://panel.kuchniavikinga.pl) meals, each dish name with its ingredients, in Home Assistant.

It creates one sensor, `sensor.kuchnia_vikinga_dzisiaj`:
- **state**: the number of meals delivered today
- **attributes**: `date`, and `meals` as a list of `{meal, name, kcal, ingredients}`

The panel is asked **once a day**. After a successful fetch it isn't contacted again until the next day. If a fetch fails, it retries at 5 minutes past the next full hour.

## Install

Copy `custom_components/kuchnia_vikinga` into `/config/custom_components/` (or add this repo to HACS as a custom repository) and restart Home Assistant.
Then go to **Settings → Devices & services → Add integration → Kuchnia Vikinga** and log in with your panel account.

## Dashboard card

A full-width section (sections view) with one collapsible row per meal; ingredients are hidden until you click a meal.

```yaml
type: grid
column_span: 4
cards:
  - type: heading
    heading: Kuchnia Vikinga – dziś
    icon: mdi:food
  - type: markdown
    grid_options:
      columns: full
    content: |-
      {%- set meals = state_attr('sensor.kuchnia_vikinga_dzisiaj', 'meals') or [] -%}
      {%- for m in meals %}
      <details>
      <summary><b>{{ m.meal }}</b> &nbsp;—&nbsp; {{ m.name }} &nbsp;<small>({{ m.kcal }} kcal)</small></summary>
      <br><small>{{ m.ingredients | join(' · ') }}</small>
      </details>
      {% if not loop.last %}<hr>{% endif %}
      {%- else %}
      <i>Brak dostawy dzisiaj.</i>
      {%- endfor %}
```

## Development

```sh
pip install -r requirements_test.txt
pytest
```
