<a href="https://lnbits.com" target="_blank" rel="noopener noreferrer">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://i.imgur.com/QE6SIrs.png">
    <img src="https://i.imgur.com/fyKPgVT.png" alt="LNbits" style="width:280px">
  </picture>
</a>

[![License: MIT](https://img.shields.io/badge/License-MIT-success?logo=open-source-initiative&logoColor=white)](./LICENSE)
[![Built for LNbits](https://img.shields.io/badge/Built%20for-LNbits-4D4DFF?logo=lightning&logoColor=white)](https://github.com/lnbits/lnbits)

# LNURLp - <small>[LNbits](https://github.com/lnbits/lnbits) extension</small>

<small>For more about LNBits extension check [this tutorial](https://github.com/lnbits/lnbits/wiki/LNbits-Extensions)</small>

## Features

- **Reusable pay links** - one QR code or link can receive many payments
- **Lightning Address** - receive payments at names like `alice@example.com`
- **Fixed or flexible amounts** - set one amount or a min/max range
- **Fiat pricing** - price in a fiat currency and convert to sats at payment time
- **Comments and success messages** - collect a short note and reply after payment
- **Webhooks** - notify another system when a link is paid
- **Nostr zaps** - receive NIP-57 zaps through a pay link

## Overview

LNURLp creates reusable Lightning payment links. The QR code stays the same, but every time someone scans it with an LNURL-compatible wallet, LNbits creates a fresh invoice for that payment.

Use LNURLp for donation pages, tip jars, checkout links, printed QR codes, Lightning Addresses, or simple payment pages that do not need a full shop.

[Wallets supporting LNURL](https://github.com/fiatjaf/awesome-lnurl#wallets)

## Usage

1. **Create** a new pay link.

   ![Create LNURLp](https://github.com/lnbits/lnurlp/blob/main/static/image/lnurlp_01.png?raw=true)

2. Fill in the basics:

   - Wallet to receive payments
   - Description shown to the payer
   - Amount, or min/max amount if it is not fixed
   - Currency, if you want fiat pricing instead of sats

3. Open the link details.

   ![LNURLp list](https://github.com/lnbits/lnurlp/blob/main/static/image/lnurlp_02.png?raw=true)

4. Share the page, copy the LNURL, write it to NFC, or print the QR code.

   ![View LNURLp](https://github.com/lnbits/lnurlp/blob/main/static/image/lnurlp_03.png?raw=true)

## Lightning Address

Add a username to a pay link to create a Lightning Address.

For example, username `alice` on `example.com` becomes:

```text
alice@example.com
```

You can also set a custom domain on the pay link. Use this when your public Lightning Address domain is different from the LNbits host.

## Fiat Amounts

Set a currency such as EUR or USD when you want the payer to pay a fiat-denominated price. LNbits converts the amount to sats when the wallet requests the invoice.

Use fixed amounts for products or donations with a set price. Use min/max amounts for tips, pay-what-you-want pages, and open donations.

## Comments and Success Actions

LNURLp can ask the payer for a short comment. This is useful for names, order notes, blog comments, or donation messages.

After payment, the payer's wallet can show:

- A success message
- A secure `https://` success URL

Use success actions for thank-you notes, download links, gated pages, or next steps after payment.

## Webhooks

Add a webhook URL when another app should be notified after a payment. LNURLp sends payment details to the webhook and can include:

- The payment hash and invoice
- The paid amount
- The payer comment
- Custom webhook data
- Optional custom headers and body data
- Zap receipt data when Nostr zaps are enabled

## Nostr Zaps

Enable zaps when the pay link should support [NIP-57](https://nips.nostr.com/57) Nostr zap payments. Admins can set the extension's Nostr private key in the LNURLp settings dialog.

When a zap payment is paid, LNURLp signs a zap receipt and sends it to the relays from the zap request.

## Disposable Pay Requests

LNURLp supports disposable and storeable pay requests. The default is disposable, which is the safest option for normal reusable QR codes and payment pages.

When enabled, wallets can save the LNURLp or lnaddress, for reuse later. [LUD-11](https://github.com/lnurl/luds/blob/luds/11.md)

Only change this if you know your wallet or integration needs storeable pay requests.

</details>

## Powered by LNbits

[LNbits](https://lnbits.com) is a free and open-source lightning accounts system.

[![Visit LNbits Shop](https://img.shields.io/badge/Visit-LNbits%20Shop-7C3AED?logo=shopping-cart&logoColor=white&labelColor=5B21B6)](https://shop.lnbits.com/)
[![Try myLNbits SaaS](https://img.shields.io/badge/Try-myLNbits%20SaaS-2563EB?logo=lightning&logoColor=white&labelColor=1E40AF)](https://my.lnbits.com/login)
