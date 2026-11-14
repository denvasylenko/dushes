---
name: salon_stats
description: How busy the salon is by day of the week, to help the user pick a quiet day.
forms: [barber_booking]
tools: ["salon_stats_tools:get_visits_by_day"]
---
When the user asks when the salon is busy or quiet: call get_visits_by_day, then show the numbers with
show_visits_chart (every day, in order, with the busiest day highlighted) and say in one sentence which day is
quietest. Use only the tool's numbers.
