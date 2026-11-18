"""
Terms of Service and Privacy Policy: the text, and their VERSIONS.

Changing a version (TERMS_VERSION / PRIVACY_VERSION) asks every user to review the documents again on their next
launch (ui/main_window_legal.py). Change it for meaningful changes only (what is collected, what is charged, rules,
rights), not for typos.

The Privacy Policy describes what this code actually does (checked 2026-11-07 against the app and the backend; the
website parts checked 2026-11-15 against Website/web and the backend's web_identity.py, payments.py, whisper_client.py
and the whisper-worker):
  sign-in       backend/discord_oauth.py (scope "identify" only; Discord's token revoked at once, never stored),
                migrations: creaper_accounts, creaper_sessions (token HASHES only), desktop utils/session.py (DPAPI)
  machine ID    desktop utils/hardware.py (SHA-256 of the Windows MachineGuid; a hashed fallback from the computer
                name and network adapter address when it can't be read)
  features      desktop services/local_engine (video and audio analysed on the PC; only moment excerpts go to the
                AI review), services/caption_engine.py (each FINISHED clip's audio -> /api/ai/transcribe, temp file
                deleted after), backend moment_review.py / related_moments.py / campaign_service.py
  records       token_transactions, creaper_token_grants, creaper_purchase_requests, creaper_policy_acks,
                creaper_clipper_jobs (48 h, job_store.KEEP_RECORDS_HOURS), highlighted_clips (user-chosen retention),
                best_moments_engine.EVAL_CACHE (memory, 24 h)
  AI providers  backend services.AI_PROVIDER_ORDER (+ extra_providers, cloudflare_ai). The text names NO provider or
                infrastructure service on purpose: users see CReaper, not how it works inside.
  website       web_identity.py (email + Argon2 password hash), payments.py (PayMongo: plan/tokens, amount, method,
                PayMongo's payment id, country; refunds by refund_plan.py), creaper_accounts preferred_name / use_case /
                heard_from, creaper_presets, /api/client-error (CLIENT_ERROR log lines), whisper-worker transcripts
                (speech audio, deleted after; RESULT_TTL_SEC 1 h) and links (LINK_FILE_TTL_SEC 30 min, captions first)
                PayMongo and Discord are named because users meet them directly; every other provider stays unnamed.
If one of these changes, update the text AND the version. Website/web/src/data/legal.json (the creaper.app /terms and
/privacy pages) is made from this file: `python desktop/services/legal_docs.py --json Website/web/src/data/legal.json`.
"""

TERMS_VERSION = "2026-11-18"
PRIVACY_VERSION = "2026-11-15"
UPDATED = "18 November 2026"
DISCLAIMER_VERSION = "2026-11-18"

BUY = "#🤝ㆍ𝖡𝖴𝖸"
PREMIUM_CHAT = "#💎ㆍ𝖯𝖱𝖤𝖬𝖨𝖴𝖬-𝖢𝖧𝖠𝖳"
SUPPORT_EMAIL = "support@creaper.app"
CONTACT_EMAIL = "contact@creaper.app"

# A document is a list of sections: (title, [paragraph | ("list", [items])])
TERMS = [
    ("Introduction", [
        "These Terms of Service (\"Terms\") govern your use of CReaper: the Windows application, the CReaper website "
        "and web app (creaper.app and app.creaper.app), their server features and the CReaper Discord community "
        "(together, the \"Service\"). CReaper is developed and operated by Adrian, an independent developer based in "
        "the Philippines (\"we\", \"us\").",
        "By installing or using CReaper, you agree to these Terms and to our Privacy Policy. If you do not agree, "
        "please do not use the Service.",
    ]),
    ("The Service", [
        "CReaper helps you turn videos into clips. Depending on where you use it, it offers:",
        ("list", [
            "AI tools (an account and a plan or tokens are needed): Auto Clipper, AI Best Moments (with Related "
            "Moments), Auto Caption, Auto Editor, Ranking and AI Reframe;",
            "editing and export: trimming, captions, styles, and an editor for the clips you make;",
            "free tools on the website, with no account needed: Audio Balancer, Video Compressor, MP3 Converter, Video "
            "Trimmer, Aspect Ratio Converter, Video to GIF, Speed Changer, Volume Booster, Video Merger, MP4 "
            "Converter, Video Reverser, Mute Video and the MP3 / MP4 converter;",
            "video links: getting a video, or only part of one, from a supported site's link.",
        ]),
        "Most processing happens on your own device. Moments are identified by CReaper's own analysis and, when AI "
        "services are available, reviewed by AI. Results depend on the source video and are provided without any "
        "guarantee of reach, engagement or accuracy.",
        "The Service is under active development. Features may be added, changed or retired over time.",
    ]),
    ("Eligibility and accounts", [
        "You must be at least 13 years old to use the Service, and at least 18 (or have the permission of a parent "
        "or guardian) to buy a plan or tokens.",
        "You can sign in with Discord or, on the website, with an email address and password. You are responsible "
        "for keeping your account secure. Activity carried out through your account is treated as your own.",
        "Access to paid features is personal to your account and, in the Windows app, is tied to the devices "
        "registered to it, as described in our Privacy Policy. You may not share, resell or transfer access, or "
        "attempt to bypass plan limits, device limits or token charges.",
    ]),
    ("Plans and tokens", [
        ("list", [
            "Plans: Essential, Plus and Elite last 30 days from purchase. Each includes a monthly token allowance and "
            "the features listed on the Pricing page for that plan, which is part of these Terms. Plans do not renew "
            "automatically: you choose to buy again. Buying a plan while one is active extends or switches it, as "
            "the checkout page states.",
            "Tokens: AI runs use tokens. The cost of each run is shown before you start it. If AI services are "
            "unavailable during a run, CReaper completes it with its own analysis and charges the lower price shown "
            "for that case. If a run fails or delivers nothing, its tokens are refunded automatically.",
            "Extra tokens can be bought by accounts with an active plan or license, and expire as shown at purchase.",
            "Premium and Freemium: these older licenses are discontinued. Since 18 November 2026, Premium "
            "licenses have been converted to the Essential plan and follow Essential's allowance, limits and 30-day "
            "period; they keep no separate allowance or refill period of their own.",
            "Tokens above your allowance: while your balance is above your plan's monthly allowance (for example "
            "after a conversion or a top-up given by staff), tools use those tokens at a higher rate (currently "
            "twice the normal price), shown before every run. Tokens bought in the Token Store are always used at "
            "the normal rate.",
            "Daily limits: each plan can make a set number of clips per day with Auto Clipper (Essential 5, Plus "
            "15, Elite 20) and fetch a set number of video links per day, as listed on the Pricing page. Links "
            "that fail to download do not count.",
            "Processing speed: Plus and Elite videos are processed ahead of Essential in CReaper's server queues "
            "and long videos are read faster; Elite is the fastest. Plus and Elite support requests are handled "
            "first. Processing and response times are not guaranteed.",
        ]),
        "Tokens have no cash value, cannot be exchanged for money, and cannot be transferred to another account.",
    ]),
    ("Purchases and payment", [
        "On the website, payments are processed by PayMongo, which accepts cards, GCash and Maya. Visitors in the "
        "Philippines see prices in Philippine pesos. Elsewhere, prices are shown in US dollars but charged in pesos "
        "at the exchange rate stated on the Pricing page and at checkout, so your bank may show a slightly different "
        "amount after its own conversion. Your plan or tokens are added once PayMongo confirms the payment. We never "
        "see or store your card, GCash or bank details.",
        "In the Windows app, tokens can also be bought through a ticket in the official CReaper Discord server, paid "
        "by GCash following instructions from authorized staff:",
        ("list", [
            "The only authorized payment recipients are @adrian and @Mark. Payments sent to anyone else are not "
            "recognized and may not be recoverable.",
            "Tokens or access are granted only after authorized staff verify your payment. Sending a payment, "
            "screenshot or message does not by itself credit your account.",
        ]),
        "Prices may change. A change never affects a plan you have already paid for.",
    ]),
    ("Refunds", [
        f"Plans: 7-day refund if unused. If you have not used any tokens from a plan, you can ask for a full refund "
        f"within 7 days of buying it: email {SUPPORT_EMAIL} from your account's email address, or open a ticket in "
        f"{BUY}, with the date of purchase. We refund the amount you paid to your original payment method, and the "
        "plan ends (an upgrade returns you to your previous plan).",
        "A plan whose tokens have been used, and token purchases, are final, apart from the automatic token refunds "
        "for failed runs described above.",
        "If the Service does not work as described, please contact support so that the issue can be investigated "
        "and resolved.",
        "Nothing in these Terms limits any rights you may have under the Consumer Act of the Philippines or any "
        "other consumer protection law that applies to you.",
    ]),
    ("Free tools and video links", [
        "The free tools run in your browser and are provided as they are. We may change them or add fair-use "
        "limits. Files you use with them stay on your device.",
        "When you paste a video link, CReaper's server fetches that video (or only the part you choose) from the "
        "site, sends it to your device and then deletes its copy. Only use links to content you have the right to "
        "use. Video sites may refuse or limit these requests; when that happens, you can download the video yourself "
        "and choose the file. CReaper does not attempt to circumvent a site's access controls.",
    ]),
    ("Acceptable use", [
        "You agree to use CReaper lawfully and responsibly. In particular, you agree not to:",
        ("list", [
            "download, edit or publish content you do not have the right to use, or use the Service to infringe the "
            "intellectual property or privacy rights of others;",
            "attempt to reverse-engineer, disrupt, overload or gain unauthorized access to the Service, its servers "
            "or other users' accounts;",
            "abuse token refunds, plan refunds, rewards, licenses, device limits or the free tools (for example by "
            "automated mass use).",
        ]),
        "You are responsible for the clips you create and for complying with the rules of any platform on which "
        "you publish them.",
    ]),
    ("Official downloads and security", [
        "The Windows app is distributed only through the official links on creaper.app and in the official CReaper "
        "Discord server. Do not install files or updates received from any other source. If you receive a "
        "suspicious file or link that claims to be CReaper, please verify it with staff before opening it.",
    ]),
    ("Third-party services", [
        "The Service relies on third-party services, including Discord for sign-in and support, PayMongo for "
        "payments, YouTube and other video platforms for source content, and third-party AI and hosting services. "
        "Your use of those services is also subject to their own terms.",
    ]),
    ("Disclaimers and limitation of liability", [
        "The Service is provided \"as is\" and \"as available\". To the extent permitted by law, we do not warrant "
        "that it will be uninterrupted, error-free or suitable for a particular purpose.",
        "To the extent permitted by law, we are not liable for indirect or consequential losses, or for loss of "
        "data, revenue or opportunity, arising from your use of the Service. Keep your own copies of clips you care "
        "about: clips stored in your browser can be lost if its data is cleared. Nothing in these Terms excludes "
        "liability that cannot be excluded under applicable law.",
    ]),
    ("Suspension and termination", [
        "We may suspend or end access to the Service for accounts that breach these Terms, abuse the Service or put "
        "other users at risk. You may stop using CReaper at any time and ask us to delete your account.",
    ]),
    ("Changes to these Terms", [
        "We may update these Terms as the Service evolves. If a change is significant, the app will ask you to "
        "review the updated Terms before you continue.",
    ]),
    ("Governing law", [
        "These Terms are governed by the laws of the Republic of the Philippines.",
    ]),
    ("Contact and support", [
        f"For help, questions or bug reports, email {SUPPORT_EMAIL}, reach out in {PREMIUM_CHAT} or open a ticket in "
        f"{BUY}. Including screenshots, error messages and a short description of what happened helps us resolve "
        "issues quickly. Suggestions are always welcome.",
    ]),
]

PRIVACY = [
    ("Introduction", [
        "This Privacy Policy explains what information CReaper collects, how it is used, who it is shared with and "
        "how long it is kept. It applies to the CReaper desktop application, the CReaper website and web app, and "
        "their servers. It describes the Service as it currently operates; much of CReaper's processing takes place "
        "on your own device.",
    ]),
    ("Information we collect", [
        ("list", [
            "Account information: when you sign in with Discord, we receive only your basic profile (the "
            "\"identify\" permission): your Discord user ID, username, display name and avatar. We do not receive "
            "your email address, server list or messages. When you sign up on the website with an email address, we "
            "store that address and a securely hashed copy of your password (never the password itself). We also "
            "record when your account was created and when you first and last signed in.",
            "About You: if you answer them, your preferred name, what you mainly use CReaper for and how you heard "
            "about it.",
            "Session information: hashed copies of your sign-in session tokens, the device or browser each session "
            "belongs to and when it was last used. Discord's own access token is revoked immediately after sign-in "
            "and is never stored.",
            "Device identifier (Windows app): a hashed device ID used for licensing, described in the next section.",
            "Plans, usage and billing records: your plan and its dates; for each run that uses tokens, the amount, "
            "its status (reserved, charged or refunded), the feature used and the time. Token grants record the "
            "amount, who granted them, the reason and the time.",
            "Payments: for each website payment, what you bought, the price, the payment method type (for example "
            "GCash or card), PayMongo's payment reference, its status (including any refund) and times, and the "
            "country used to price it. For purchases through Discord: the token amount, price, reference code and "
            "status of the request, and which staff member credited it.",
            "Country: on the website, your country (estimated from your IP address by our hosting provider) chooses "
            "the currency you see. We do not store your IP address for this.",
            "Saved presets: editing and brand presets you save, including any logo image you add.",
            "Error reports: if the website crashes, it sends us the error message, the page address, technical "
            "details of the error and your browser type, so we can fix it. They do not include your account or your "
            "files.",
            "Content you choose to send: the information described under \"Video and transcript processing\" below.",
            "Policy acknowledgements: which version of these documents you acknowledged, and when.",
        ]),
    ]),
    ("Device identifier", [
        "CReaper generates a device identifier to enforce licensing and prevent license abuse. It is a SHA-256 hash "
        "of your Windows installation identifier (MachineGuid). If that identifier cannot be read, a hash derived "
        "from your computer name and network adapter address is used instead. Only the hash is transmitted; the "
        "underlying values never leave your computer.",
        "The device identifier is stored with your sessions, licenses and registered devices. It is used only to "
        "verify that a license is used on the devices registered to it, and not for advertising or tracking.",
        "If you connect the app to the CReaper website, we also store that device's name, platform, app version, "
        "last-seen time, a hashed copy of its connection secret, and the jobs you send to it from the website (the "
        "video link and your chosen settings).",
    ]),
    ("Video and transcript processing", [
        "In the Windows app, videos are processed on your computer. This includes downloading, trimming, moment "
        "analysis and rendering. Transcripts of the source video are obtained by your computer from the video's own "
        "captions or generated locally by an on-device speech model.",
        "On the website, the videos you choose are processed in your browser: trimming, analysis, face tracking, "
        "captions, rendering and all free tools. Your video files are not uploaded, with two exceptions:",
        ("list", [
            "Transcripts: for AI tools and Auto Caption, the video's audio track (compressed speech audio, not the "
            "video) is uploaded to CReaper's own transcription server. It is deleted once the transcript is made, "
            "and the transcript is kept there for at most 1 hour so your browser can collect it.",
            "Video links: when you paste a link, CReaper's server downloads that video (or only the part you "
            "choose), sends it to your browser and deletes its copy within 30 minutes. For YouTube links, CReaper may "
            "first read the video's own captions and viewing-activity data so that AI Best Moments can find moments "
            "before downloading anything. These requests may pass through a network proxy service and contain the "
            "video link only, never your account.",
        ]),
        "Depending on the features you use, the following is also sent to our server:",
        ("list", [
            "Moment review: the words spoken in the strongest candidate moments and the sentence or two just "
            "before each (short excerpts, not the full transcript), with their times, CReaper's scores and the kind "
            "of video CReaper recognised (for example gaming or podcast), so that they can be reviewed by AI. The "
            "video's tags and description are only read on your device, to recognise the kind of video.",
            "Pricing: the video's length and the time of the latest moment used, so the run can be priced.",
            "Captions in the Windows app: when captions are turned on, the audio of each finished clip (not the "
            "source video) is sent to our server and transcribed by a third-party speech recognition service to "
            "time the caption words. Our server deletes its copy of the audio as soon as the captions are made.",
            "Campaign rules in Auto Clipper: the full transcript and the text of the requirements file you upload, "
            "so the rules can be checked.",
            "Saved Highlights: the clip's title, link, times, scores, descriptions and transcript, kept for the "
            "number of days you select.",
        ]),
    ]),
    ("How we use information", [
        ("list", [
            "to authenticate you and keep you signed in;",
            "to provide the features you request, including AI review of moments, transcripts and video links;",
            "to calculate, reserve, charge and refund tokens, and to process payments, purchase requests and "
            "refunds;",
            "to enforce plan, licensing and device limits and prevent abuse;",
            "to personalise the app (your preferred name), to understand which features matter (About You answers, "
            "looked at as totals) and to handle support requests by plan level;",
            "to show your own rank on the Statistics page, based on the number of completed runs recorded for each "
            "account (only your own position is shown);",
            "to diagnose problems and keep the Service reliable and secure.",
        ]),
        "The Statistics page itself is computed from a record stored only on your device and is not transmitted. "
        "The website also keeps your clips, runs and preferences in your browser's storage; we do not receive them.",
    ]),
    ("AI processing", [
        "To review moments and time captions, our server sends the text and clip audio described above to "
        "third-party AI service providers. These requests contain video content only, not your account or device "
        "identifier. The providers process this content to return a result and handle it under their own terms and "
        "privacy policies.",
        "To avoid repeating identical requests, AI evaluations of moment text may be held in server memory for up to "
        "24 hours.",
        "If you use your own AI service key, it is stored encrypted on your computer and sent with your requests so "
        "that they use your key. Our server uses it only for those requests and does not retain it.",
        "If AI services are unavailable, CReaper completes the run using its own analysis on your device.",
    ]),
    ("Service providers and disclosure", [
        "We use the following service providers to operate CReaper:",
        ("list", [
            "Discord: sign-in, community, support and purchase tickets;",
            "PayMongo: website payments and refunds;",
            "cloud database, hosting, email and network providers, which store account, token, payment, preset and "
            "Highlight records, run the CReaper servers and website, and send verification and security emails;",
            "third-party AI service providers, for moment review and caption timing only.",
        ]),
        "We do not sell your personal information. We may disclose information where required by law.",
        "The CReaper app, website and servers never receive or store your card, GCash, Maya or banking details.",
    ]),
    ("Retention", [
        ("list", [
            "Account, plan, license, device, token and payment records: for as long as your account exists (payment "
            "records may be kept longer where tax or accounting law requires it).",
            "About You answers and saved presets: until you change or delete them, or delete your account.",
            "Uploaded speech audio: deleted once transcribed; transcripts: up to 1 hour on the server.",
            "Video-link downloads: deleted from the server within 30 minutes.",
            "Auto Clipper job records (status, results and technical diagnostics): 48 hours.",
            "Saved Highlights: for the number of days you select when saving.",
            "AI evaluation cache: up to 24 hours, in memory only.",
            "Server logs, including error reports: kept by our hosting provider for troubleshooting, with secret "
            "keys removed.",
            "Information stored on your device (settings, caches, clips, debug log, statistics): until you clear it "
            "or uninstall CReaper.",
        ]),
    ]),
    ("Security", [
        "Passwords, session tokens and device secrets are stored on our server only in hashed form, sign-in is "
        "protected against repeated guessing, and connections are encrypted. In the Windows app, your sign-in token "
        "and any personal API key are encrypted using Windows data protection, so only your Windows user account can "
        "read them. No system is completely secure, but we work to protect the information we hold.",
    ]),
    ("Your rights and choices", [
        "Under the Data Privacy Act of 2012 (Republic Act No. 10173), you may request access to, correction of, or "
        f"deletion of your personal information. To make a request, email {CONTACT_EMAIL} or open a ticket in {BUY}.",
        "You can also change your About You answers and preferred name, delete presets and saved Highlights, sign "
        "out of every session, and clear data stored in your browser or the app (Settings > Storage).",
    ]),
    ("Changes to this Policy", [
        "We will update this Policy when our practices change. If a change is significant, the app will ask you to "
        "review the updated Policy before you continue.",
    ]),
    ("Contact", [
        f"For privacy questions or requests, email {CONTACT_EMAIL} or open a ticket in {BUY} in the official CReaper "
        "Discord server.",
    ]),
]


DISCLAIMER = [
    ("About this page", [
        "This Disclaimer and Copyright (DMCA) Policy is part of the CReaper Terms of Service. It explains what CReaper "
        "is and isn't responsible for, and how to report content that infringes your copyright.",
    ]),
    ("No warranty", [
        "The Service is provided \"as is\" and \"as available\", without warranties of any kind, express or "
        "implied, including fitness for a particular purpose, accuracy, availability or non-infringement. CReaper "
        "does not promise that the Service will be uninterrupted, error-free or secure, or that clips will reach any "
        "audience, views, engagement or earnings.",
    ]),
    ("Limitation of liability", [
        "To the fullest extent permitted by law, CReaper and its developer are not liable for any indirect, "
        "incidental, special, consequential or punitive damages, or for any loss of data, content, accounts, "
        "followers, revenue, profits or opportunities, arising from or related to your use of, or inability to use, "
        "the Service, even if advised of the possibility.",
        "This includes, without limitation:",
        ("list", [
            "anything that happens to your accounts on other platforms (YouTube, TikTok, Instagram, Facebook, X, "
            "Twitch, Kick or any other), including strikes, claims, takedowns, demonetization, bans or reduced reach;",
            "anything that happens to your CReaper account or Discord account because of shared, leaked or stolen "
            "login details, devices you don't control, or links and files you open;",
            "payments made to anyone other than CReaper's checkout or its authorized staff in the official Discord "
            "server, and scams by people pretending to be CReaper;",
            "clips, captions, titles or hooks that are inaccurate, offensive or unsuitable: you review everything "
            "before you post it;",
            "outages, delays or changes of third-party services CReaper relies on.",
        ]),
        "Where liability cannot be excluded, CReaper's total liability for all claims is limited to the amount you "
        "paid CReaper in the 30 days before the claim. Nothing here limits rights you have under laws that cannot be "
        "waived, such as consumer protection laws that apply to you.",
    ]),
    ("Your content and responsibility", [
        "You are solely responsible for the videos, links and other material you use with CReaper and for what you "
        "do with the clips you make, including having the rights or permission needed to edit and publish them. "
        "CReaper does not publish anything on your behalf and is not a hosting or sharing service: your clips are "
        "made for you and kept only as described in our Privacy Policy.",
        "CReaper is not affiliated with, endorsed by or sponsored by YouTube, TikTok, Instagram, Facebook, X, "
        "Twitch, Kick, Discord or any other platform named on the Service. Getting a video from a link is subject to "
        "that platform's terms, which you are responsible for following.",
    ]),
    ("Copyright and DMCA notices", [
        "CReaper respects copyright. If you believe material processed or made available through the Service "
        f"infringes your copyright, email {SUPPORT_EMAIL} with the subject \"DMCA notice\" and include:",
        ("list", [
            "your physical or electronic signature;",
            "the copyrighted work you claim is infringed;",
            "the material you claim is infringing and enough information for us to locate it;",
            "your name, address, telephone number and email address;",
            "a statement that you have a good-faith belief the use is not authorized by the owner, its agent or the "
            "law;",
            "a statement that the information in the notice is accurate and, under penalty of perjury, that you are "
            "the owner or authorized to act for the owner.",
        ]),
        "If your material was removed because of a notice and you believe that was a mistake, you can send a "
        "counter-notice to the same address with your contact details, the material removed, and a statement under "
        "penalty of perjury that you believe it was removed by mistake. We may share notices with the other party.",
        "Accounts of people who repeatedly infringe copyright may be suspended or closed.",
    ]),
    ("Contact", [
        f"Questions about this page: {SUPPORT_EMAIL}.",
    ]),
]


def as_json() -> dict:
    """The creaper.app pages' data (Website/web/src/data/legal.json): the same text, as {"p"} / {"list"} blocks."""
    def doc(sections):
        return [{"title": t, "blocks": [{"list": list(b[1])} if isinstance(b, tuple) else {"p": b} for b in blocks]}
                for t, blocks in sections]
    return {"termsVersion": TERMS_VERSION, "privacyVersion": PRIVACY_VERSION, "updated": UPDATED,
            "disclaimerVersion": DISCLAIMER_VERSION,
            "terms": doc(TERMS), "privacy": doc(PRIVACY), "disclaimer": doc(DISCLAIMER)}


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--json":
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            json.dump(as_json(), f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("wrote", sys.argv[2])
    else:
        print("usage: python legal_docs.py --json Website/web/src/data/legal.json")
