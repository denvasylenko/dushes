## ADDED Requirements

### Requirement: Cards as an A2UI catalog (idea)
If the spike passes, the widget's blocks SHALL be published as an A2UI catalog, and a card SHALL be renderable from A2UI messages sent over AG-UI, within the one-script bundle's size budget.

#### Scenario: An hours card from A2UI
- **WHEN** the agent sends an A2UI message for the opening-hours card
- **THEN** <agui-chat> draws it as it draws the block card today
