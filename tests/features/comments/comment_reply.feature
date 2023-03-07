Feature: Replying to a comment on phone
  As a user,
  I can reply to a comment on my phone

  Scenario: Rincewind replies to a comment from Twoflower
    Given Rincewind is a participant in Ankh-Morpork 2010
    And Twoflower has left a comment
    When Rincewind taps on "Reply" to the comment on his phone
    Then a reply screen opens
    And Twoflower's comment alone is visible on the screen
    And the keyboard opens for Rincewind to type
    And Rincewind can see that the reply will come from his account, just in case he was managing multiple accounts and momentarily confused about which account was in use
    And Rincewind's reply is visible in a text box just above the keyboard
    And the text box is a single line initially but grows up to X lines/Y size to fit the text that is being typed
    And when he types, his avatar is replaced with a send button
    And when he presses the send button, his reply is posted and appears in the comments
