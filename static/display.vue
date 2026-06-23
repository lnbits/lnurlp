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
          <h6
            class="text-subtitle1 q-mb-sm q-mt-none"
            v-text="$t('lnurlp.lnbits_pay_link')"
          ></h6>
          <p class="q-my-none" v-text="$t('lnurlp.pay_with_wallet')"></p>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <q-expansion-item
              group="extras"
              icon="info"
              :label="$t('lnurlp.powered_by_lnurl')"
            >
              <q-card>
                <q-card-section>
                  <p v-text="$t('lnurlp.lnurl_description')"></p>
                  <p v-text="$t('lnurlp.lnurl_exploring')"></p>
                  <i18n-t keypath="lnurlp.lnurl_more_info" tag="small">
                    <template #link>
                      <a
                        class="text-secondary"
                        href="https://github.com/fiatjaf/awesome-lnurl"
                        target="_blank"
                        >Awesome LNURL</a
                      >
                    </template>
                  </i18n-t>
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>
  </div>
</template>
