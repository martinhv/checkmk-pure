Feature: FlashArray WATO plugin

  Scenario: The WATO plugin should be visible
    Given I logged in
    When I navigate to the "Other integrations" page
    Then I should see "Pure Storage FlashArray"
