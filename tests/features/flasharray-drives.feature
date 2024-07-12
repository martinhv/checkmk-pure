Feature: FlashArray drives reporting

  Background:
    Given I logged in
    And I configured a FlashArray as the "FlashArray" host

  Scenario: I should see a FlashArray host
    When I navigate to the "All hosts" page
    Then I should see "FlashArray"
