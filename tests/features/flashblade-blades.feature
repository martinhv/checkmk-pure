Feature: FlashBlade blades reporting

  Background:
    Given I logged in
    And I configured a FlashBlade as the "FlashBlade" host

  Scenario: I should see a FlashBlade host
    When I navigate to the "All hosts" page
    Then I should see "FlashBlade"
