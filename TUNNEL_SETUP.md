# 📱 Access the dashboard from your phone (private, via Tailscale)

This keeps **all your financial data on your Mac** — Tailscale builds an encrypted private
network ("tailnet") between *your own devices*. Nothing is exposed to the public internet.

**Time:** ~10 minutes. **Cost:** free (personal plan). **You need:** your Mac + your phone.

---

## Step 1 — Install Tailscale on your Mac
1. Get it from the Mac App Store (search "Tailscale") or https://tailscale.com/download.
2. Open Tailscale, **Log in**, and sign in with Google/Apple/email. Create the account.
3. You'll see a green "Connected" state. That's it — your Mac is on your tailnet.

## Step 2 — Install Tailscale on your phone
1. Install **Tailscale** from the App Store (iPhone) / Play Store (Android).
2. **Log in with the same account** you used on the Mac.
3. Toggle the VPN **On** when prompted (it's a private tunnel, not a real VPN service).

> Now your Mac and phone can reach each other privately, even on different networks (your
> phone on cellular still works).

## Step 3 — Start the dashboard server on your Mac
In Terminal:
```
cd "/Users/nhihad/Claude Local/Expense Tracker"
python3 server.py
```
It prints the addresses it's reachable at, e.g.:
```
On this Mac                    http://localhost:8765/
On your Wi-Fi (LAN)            http://192.168.2.134:8765/
On your phone via Tailscale    http://100.x.y.z:8765/   ← appears once Tailscale is running
```
*(Tip: double-click `run-server.command` in Finder instead of typing — same thing.)*

## Step 4 — Find your Mac's Tailscale address
Either read it from the server banner (Step 3), or run:
```
tailscale ip -4
```
→ something like `100.101.102.103`. You can also use the Mac's **tailnet name**
(Tailscale admin console → Machines → your Mac, e.g. `my-macbook.tailXXXX.ts.net`).

## Step 5 — Open it on your phone
With Tailscale **On** on the phone, open your browser to:
```
http://100.101.102.103:8765/
```
(use your Mac's Tailscale IP from Step 4). The full dashboard loads — 4 cards, chequing,
subscriptions, charts, uploads, rules — all live. **Add it to your home screen** (Share →
Add to Home Screen) for an app-like icon (uses the favicon).

---

## Keep it running

The server only works while `python3 server.py` is running on your Mac (and the Mac is awake).

**Simplest:** leave the Terminal window open. To stop, press `Ctrl-C`.

**Always-on (auto-start at login):** install the included launchd job —
```
cp com.expensetracker.server.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.expensetracker.server.plist
```
Now it starts automatically and restarts if it crashes. To stop/remove:
```
launchctl unload ~/Library/LaunchAgents/com.expensetracker.server.plist
```
*(Prevent your Mac from sleeping while you want remote access: System Settings → Lock Screen /
Battery → set "turn display off" but keep the Mac awake, or run `caffeinate -s` in a Terminal.)*

---

## Optional: a clean HTTPS URL (no IP, no browser warning)
Tailscale can serve it at a tidy HTTPS address on your tailnet:
```
tailscale serve --bg 8765
```
Then open `https://<your-mac-name>.tailXXXX.ts.net/` on your phone. (Enable **HTTPS
Certificates** + **MagicDNS** in the Tailscale admin console first.) To stop: `tailscale serve --https=443 off`.

---

## Security notes
- Your data never leaves your Mac; the tunnel is private to devices signed into **your**
  Tailscale account. Don't enable **Funnel** (that's the one that exposes things publicly).
- The dashboard is read/write (uploads, rule edits) — only your own devices can reach it.
- If you ever want to revoke a device, remove it in the Tailscale admin console.
