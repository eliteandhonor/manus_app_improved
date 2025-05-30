# Batch Login and Clear Logins Feature Plan

## 1. Batch Login ("Run All Logins") Feature

- **UI:** Add a "Run All Logins" button to the Automation tab.
- **Behavior:** When clicked, the app will:
  - Iterate through all saved sites in order.
  - For each site:
    - If the Google login flag is set, open the system browser and wait for user "Continue" confirmation before proceeding to the next site.
    - If not, run Playwright automation as normal.
    - Show progress and results in the status tree.
  - Always attempt all sites, regardless of previous login status.
  - Allow interruption/cancellation if needed (future enhancement).

- **Error Handling:** If a login fails, display the error and continue to the next site.

## 2. Clear Logins Feature

- **UI:** Add a "Clear Logins" button to the Automation tab.
- **Behavior:** When clicked, the app will:
  - Clear the status tree (login history/status display).
  - Reset the "last login" timestamp for all sites, so the user can re-run all logins as if starting fresh.
  - Optionally, confirm with the user before clearing.

## 3. Batch Login Flow (Mermaid Diagram)

```mermaid
flowchart TD
    A[User clicks "Run All Logins"] --> B{Sites left?}
    B -- Yes --> C[Check Google login flag]
    C -- Google Login --> D[Open system browser, wait for user "Continue"]
    D --> E[Proceed to next site]
    C -- Automated --> F[Run Playwright automation]
    F --> E
    E --> B
    B -- No --> G[Batch login complete]
```

## 4. Summary Table

| Feature         | UI Location      | Action/Effect                                      |
|-----------------|-----------------|----------------------------------------------------|
| Run All Logins  | Automation tab  | Runs login for all sites in order, waits for manual confirmation if needed, always attempts all |
| Clear Logins    | Automation tab  | Clears status display and resets last login timestamps for all sites |

---

**This plan will provide a seamless batch login experience and allow users to easily reset and re-run all logins without restarting the app.**