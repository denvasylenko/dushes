# Spec Delta

## MODIFIED Requirements

### Requirement: Answers from the site
Dushes SHALL answer only from the site map's sections, the current page's context (see `page-context`) and its tools, and name the page or section it used; when none of them answers, it SHALL say so.

#### Scenario: A question about opening hours
- **WHEN** the user asks when the branch is open
- **THEN** the answer comes from the contacts page and the reply offers to go there

#### Scenario: A question about the screen
- **WHEN** the user on the Loans page asks "what does APR mean in this table?" and the page sends the table
- **THEN** the answer explains the column using the table's values and names the section
