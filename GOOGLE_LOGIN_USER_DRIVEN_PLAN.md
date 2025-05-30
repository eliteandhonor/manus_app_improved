# User-Driven Google Login Detection and Workflow Plan

## 1. Credential Management UI Changes
- Add a checkbox or toggle in the "Add Website" and "Edit Website" dialogs:  
  **[ ] This site uses Google login**
- Store this flag with each website's credentials.
- **Allow the user to edit the Google login flag directly from the credentials list** (e.g., right-click or inline toggle in the credentials table).

## 2. Login Workflow Logic
- When the user initiates login:
  1. **Check the "Google login" flag for the site.**
  2. **If checked:**
     - Open the system browser (default user browser) to the login page.
     - Show a modal dialog:  
       "Please log in manually in your browser. When finished, click Continue."
     - After the user clicks "Continue", proceed to the next login (if batch).
  3. **If not checked:**
     - Proceed with automated login using Playwright as normal.

## 3. Automation Tab Changes
- **Add an option to toggle the Google login flag from the Automation tab** before starting login (e.g., a checkbox or context menu for the selected site).

## 4. Batch Login Support
- If the user is logging into multiple sites, after each manual Google login, show the "Continue" popup and then proceed to the next site automatically.

---

## Mermaid Diagram: User-Driven Google Login Workflow

```mermaid
flowchart TD
    A[User initiates login] --> B{Does site use Google login?}
    B -- Yes --> C[Open system browser for manual login]
    C --> D[Show "Continue" popup after user logs in]
    D --> E[Proceed to next login or finish]
    B -- No --> F[Automate login with Playwright]
    F --> E
```

---

## Summary Table

| Step                | Google Login Flag | Action                                 | User Experience                |
|---------------------|------------------|----------------------------------------|--------------------------------|
| Add/Edit Website    | User sets flag   | Checkbox in dialog                     | Simple, explicit               |
| Credentials List    | User edits flag  | Inline toggle or right-click menu      | Fast, convenient               |
| Automation Tab      | User toggles flag| Checkbox/context menu for selection    | Flexible, on-the-fly           |
| Start Login         | Checked          | System browser + "Continue" popup      | Manual, but guided             |
| Start Login         | Not checked      | Playwright automation                  | Fully automated                |
| Batch Login         | Mixed            | Handles each site per its flag         | Seamless, minimal prompts      |

---

**This plan ensures maximum automation for non-Google sites, while making Google login as simple and user-driven as possible, with flexible flag editing from both the credentials list and the automation tab.**