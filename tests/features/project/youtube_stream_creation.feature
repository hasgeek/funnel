Feature: Youtube live stream creation on project page

  Scenario: Create youtube live stream
    Given Vetinari is an editor of the Ankh-Morpork 2010 project
    And the front matter of the project exists
    When Vetinari creates live stream from the project page
    Then the live stream gets created on youtube with the details from the front matter
    And the link is embeded on the project page
