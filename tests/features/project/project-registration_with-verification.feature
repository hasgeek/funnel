Feature: Project registration with contact verification
    
Background: 
    Given I am on the project page
    And I am willing to share contact my contact information

Scenario: User is logged-in
    Given I am logged-in to my account
    When I click the JOIN FREE button
    Then I should see a pop-up modal asking for consent to share my contact info with the project promoter 
    And I click CONFIRM to consent
    And I am redirected to the project page
    And the project registration count increments by 1

Scenario: User has an account and is not logged-in
    Given I am not logged-in to my account
    When I click the JOIN FREE button
    And I successfully login to my account
    Then I should see a pop-up modal asking for consent to share my contact info with the project promoter 
    And I click CONFIRM to consent
    And I am redirected to the project page
    And the project registration count increments by 1

Scenario: User has an account and enters invalid phone number to log-in
    Given I am not logged-in to my account
    When I click the JOIN FREE button
    And I enter an invalid phone number
    Then I should an error message below the input field

Scenario: User has an account and enters invalid email address/password to log-in
    Given I am not logged-in to my account
    When I click the JOIN FREE button
    And I enter an invalid email address/password pair
    Then I should an error message below the password field 

Scenario: User has an account and has forgotten the log-in password
    Given I am not logged-in to my account
    When I click the JOIN FREE button
    And I choose to log-in using email
    And I click forgot password
    Then I should be redirected to the 'Reset password' page

Scenario: User does not have an account
    Given I do not have a user account
    When I click the JOIN FREE button
    And I enter valid contact information
    And I enter my name in the 'Your name' input field
    And I successfully verify with a valid OTP
    Then I should see a pop-up modal asking for consent to share my contact info with the project promoter 
    And I click CONFIRM to consent
    And I am redirected to the project page
    And the project registration count increments by 1

Scenario: User does not have an account and enters an invalid phone-number to create an account
    Given I do not have a user account
    When I click the JOIN FREE button
    And I enter an invalid phone number
    Then I should an error message below the input field

Scenario: User does not have an account and enters an invalid email address to create an account
    Given I do not have a user account
    When I click the JOIN FREE button
    And I enter an invalid email address
    Then OTP message delivery will fail


