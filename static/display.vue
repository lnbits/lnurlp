<template id="page-lnurlp-public">
  <div class="row q-col-gutter-md justify-center">
    <div class="col-12 col-sm-6 col-md-5 col-lg-4">
      <q-card class="q-pa-lg">
        <q-card-section class="q-pa-none">
          <div class="text-center">
            <lnbits-qrcode-lnurl :url="url" :nfc="true"></lnbits-qrcode-lnurl>
          </div>
        </q-card-section>
      </q-card>
    </div>
    <div class="col-12 col-sm-6 col-md-5 col-lg-4 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6 class="text-subtitle1 q-mb-sm q-mt-none">
            LNbits LNURL-pay link
          </h6>
          <p class="q-my-none">
            Use an LNURL compatible bitcoin wallet to pay.
          </p>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <q-expansion-item
              group="extras"
              icon="info"
              label="Powered by LNURL"
            >
              <q-card>
                <q-card-section>
                  <p>
                    LNURL is a range of lightning-network standards that allow
                    us to use lightning-network differently. An LNURL-pay is a
                    link that wallets use to fetch an invoice from a server
                    on-demand. The link or QR code is fixed, but each time it is
                    read by a compatible wallet a new QR code is issued by the
                    service. It can be used to activate machines without them
                    having to maintain an electronic screen to generate and show
                    invoices locally, or to sell any predefined good or service
                    automatically.
                  </p>
                  <p>
                    Exploring LNURL and finding use cases, is really helping
                    inform lightning protocol development, rather than the
                    protocol dictating how lightning-network should be engaged
                    with.
                  </p>
                  <small
                    >Check
                    <a
                      class="text-secondary"
                      href="https://github.com/fiatjaf/awesome-lnurl"
                      target="_blank"
                      >Awesome LNURL</a
                    >
                    for further information.</small
                  >
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
