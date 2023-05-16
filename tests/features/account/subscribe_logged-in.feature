Feature: Account Subscribe
  As a user,
  I want to subscribe to an organization,
  So I can participate in the activities of the organization

  Background:
    Given the user the logged in
    And is on a project page that has the subscribe option
    And wants to buy an individual subscription

  Scenario: User opens the subscription modal
    Given the user clicks the 'Subscription pricing' button
    When the user chooses one of the individual subscription options
    Then the user sees the 'Subscription pricing' modal pop-up

  Scenario: User proceeds to checkout
    Given the user has read the details about the subscription tier
    And reviewed the order summary
    When the user clicks the checkout button
    Then the user sees the contact form
    And the payment button appears at the bottom of the form

  Scenario: User proceeds to make payment
    Given the user leaves the 'Gift subscription' checkbox unchecked
    And has filled the contact form with relevant details
    When the user clicks the payment button
    Then the user sees the payment options screen
    And the 'Pay now' button appears at the bottom of the screen

  Scenario: User chooses to gift subscription
    Given the user checks the 'Gift subscription' checkbox
    And enters a valid username
    When the user clicks the payment button
    Then the user sees the payment options screen
    And the 'Pay now' button appears at the bottom of the screen

  Scenario: User chooses to pay by card
    Given the user is on the payment options screen
    And has chosen the card payment option
    When the user enters valid card details and clicks 'Pay now'
    Then the user is redirected to the payment gateway interface
    And is prompted to enter a valid OTP

  Scenario: User chooses to pay by internet banking
    Given the user is on the payment options screen
    And has chosen the internet banking payment option and clicks 'Pay now'
    When the user is redirected to the payment gateway internet banking login interface
    And logs in using a valid username and password
    Then the user is prompted to enter a valid OTP

  Scenario: User chooses to pay by UPI
    Given the user is on the payment options screen
    And has chosen the UPI payment option
    When the user enters a valid VPA and clicks 'Pay now'
    Then the user is prompted to open their UPI app and complete the payment

  Scenario: User successfully completes the payment
    Given the user on the final payment step
    And enters a valid PIN or OTP and clicks 'Pay' or 'Submit'
    When the payment gateway records a successful transaction
    Then the user is redirected to a 'Payment successful' modal
    And sees buttons to RSVP and change contact options appear on the project page.

  Scenario: User fails to complete the payment
    Given the user on the final payment step
    And enters a invalid PIN or OTP and clicks 'Pay' or 'Submit'
    When the payment gateway records a failed transaction
    Then the user sees a 'Payment Error' message
    And sees button to 'Retry payment'

  Scenario: User buys a corporate subscription
    Given the user proceeds to buy a corporate subscription
    When the user successfully completes the payment process
    Then the user is redirected to a 'Payment successful' modal
    And sees a button to 'Assign subscribers' in the modal
    And sees buttons to RSVP and change contact options appear on the project page.

  Scenario: Corporate subscriber chooses to assign subscribers
    Given the user has successfully purchased a corporate subscription
    And is on the 'Payment successful' modal
    When the subscriber clicks the 'Assign subscribers' button
    Then the user is redirected to form with input fields for the 9 remaining subscriber slots
    And the user enters valid details and completes the assigning process

  Scenario: Corporate subscriber chooses not to assign subscribers
    Given the user has successfully purchased a corporate subscription
    And is on the 'Payment successful' modal
    When the subscriber clicks the 'Close' button
    Then the user is redirected to the project page
    And sees buttons to RSVP and change contact options appear on the project page.
