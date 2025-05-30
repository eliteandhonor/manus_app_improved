# Automated Login Manager – Overview & Monetization

## Introduction

The Automated Login Manager is a user-friendly desktop application designed to streamline and automate the process of logging into websites. It supports both manual (Google/system browser) and automated (Playwright-driven) login workflows, batch login operations, and robust credential management—all within an intuitive graphical interface.

---

## Key Features

- **Credential Management:** Add, edit, and batch-clear website credentials.
- **Google/Manual Login Detection:** Automatically detects when a site requires Google login and prompts the user to use the system browser.
- **Automated Login:** Uses Playwright to automate logins for standard sites.
- **Batch Login:** "Run All Logins" feature automates login for all saved sites in sequence.
- **Clear Logins:** Resets login statuses and timestamps for all sites.
- **User-Friendly UI:** Built with Tkinter for a clean, accessible experience.

---

## Workflow Overview

1. **User selects a website** and chooses to log in (either individually or via batch).
2. **App checks** if the site requires Google login:
    - If **yes**, the system browser is launched for manual login, and the user is prompted to confirm completion.
    - If **no**, Playwright automates the login process.
3. **After every login** (manual or automated), a monetization link is opened in a new browser tab.
4. **Batch login** repeats this process for each site in the list.

### Login & Monetization Flow

```mermaid
flowchart TD
    Start([Start Login]) --> CheckGoogle{Google Login?}
    CheckGoogle -- Yes --> Manual[Manual Login in System Browser]
    Manual --> Monetize1[Open Monetization Link in New Tab]
    CheckGoogle -- No --> Automated[Automated Login (Playwright)]
    Automated --> Monetize2[Open Monetization Link in New Tab]
    Monetize1 & Monetize2 --> End([Login Complete])
```

---

## Monetization <money>

After every login—whether manual (Google/system browser) or automated (Playwright), and for each site in batch mode—the app opens a monetization link in a new browser tab:

```
https://otieu.com/4/8811956
```

- This process is **seamless** and does **not interfere** with the user’s workflow.
- The link is an ad/affiliate URL, generating revenue for the app owner each time it is opened.
- Monetization is triggered automatically after every login event, ensuring consistent revenue generation.

---

## How It Works (Technical)

- The monetization link is opened in the code immediately after each login completes, regardless of the login method.
- This is implemented in both the single login and batch login workflows, ensuring every login triggers the monetization mechanism.

---

## Conclusion

The Automated Login Manager delivers robust, user-friendly login automation for a variety of websites, with a transparent and non-intrusive monetization strategy. By opening a monetization link after every login, the app generates revenue while maintaining a seamless experience for users.