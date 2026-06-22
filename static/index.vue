<template id="page-lnurlp">
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-7 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <q-btn
            unelevated
            color="primary"
            :label="$t('lnurlp.new_pay_link')"
            @click="formDialog.show = true"
          ></q-btn>
          <lnbits-extension-settings-btn-dialog
            v-if="g.user.admin"
            :endpoint="endpoint"
            :options="settings"
          />
        </q-card-section>
      </q-card>

      <q-card>
        <q-card-section>
          <div class="row items-center no-wrap q-mb-md">
            <div class="col">
              <h5
                class="text-subtitle1 q-my-none"
                v-text="$t('lnurlp.pay_links')"
              ></h5>
            </div>
            <div class="col q-ml-lg">
              <q-input
                borderless
                dense
                debounce="300"
                v-model="payLinksFilter"
                :placeholder="$t('search')"
              >
                <template v-slot:append>
                  <q-icon name="search"></q-icon>
                </template>
              </q-input>
            </div>
          </div>
          <q-table
            dense
            flat
            :rows="payLinks"
            :columns="payLinksTable.columns"
            row-key="id"
            :filter="payLinksFilter"
            v-model:pagination="payLinksTable.pagination"
          >
            <template v-slot:header="props">
              <q-tr class="text-left" :props="props">
                <q-th auto-width></q-th>
                <q-th v-for="col in props.cols" :key="col.name" :props="props">
                  <span v-text="col.label"></span>
                </q-th>
                <q-th auto-width></q-th>
              </q-tr>
            </template>
            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td auto-width>
                  <q-btn
                    unelevated
                    dense
                    size="xs"
                    icon="launch"
                    :color="$q.dark.isActive ? 'grey-7' : 'grey-5'"
                    type="a"
                    :href="props.row.pay_url"
                    target="_blank"
                    class="q-ml-sm"
                  >
                    <q-tooltip>
                      <span v-text="$t('lnurlp.shareable_page')"></span>
                    </q-tooltip>
                  </q-btn>
                  <q-btn
                    dense
                    size="xs"
                    icon="visibility"
                    :color="$q.dark.isActive ? 'grey-7' : 'grey-5'"
                    class="q-ml-sm"
                    @click="openQrCodeDialog(props.row.id)"
                  >
                    <q-tooltip>
                      <span v-text="$t('lnurlp.view_link')"></span>
                    </q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="openUpdateDialog(props.row.id)"
                    icon="edit"
                    color="light-blue"
                    class="q-ml-sm"
                  >
                    <q-tooltip>
                      <span v-text="$t('update')"></span>
                    </q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="deletePayLink(props.row.id)"
                    icon="cancel"
                    color="pink"
                    class="q-ml-sm"
                  >
                    <q-tooltip>
                      <span v-text="$t('delete')"></span>
                    </q-tooltip>
                  </q-btn>
                </q-td>
                <q-td
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                  v-text="col.value"
                ></q-td>
                <q-td>
                  <q-icon v-if="props.row.webhook_url" size="14px" name="http">
                    <q-tooltip>
                      <span v-text="$t('lnurlp.webhook_to')"></span>
                      <span v-text="props.row.webhook_url"></span>
                    </q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.success_text || props.row.success_url"
                    size="14px"
                    name="call_to_action"
                  >
                    <q-tooltip>
                      <span
                        v-text="
                          $t('lnurlp.on_success_message', {
                            message: props.row.success_text
                          })
                        "
                      ></span>
                      <span
                        v-if="props.row.success_url"
                        v-text="
                          $t('lnurlp.on_success_and_url', {
                            url: props.row.success_url
                          })
                        "
                      ></span>
                    </q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.comment_chars > 0"
                    size="14px"
                    name="insert_comment"
                  >
                    <q-tooltip>
                      <span
                        v-text="
                          $t('lnurlp.comment_chars_allowed', {
                            chars: props.row.comment_chars
                          })
                        "
                      ></span>
                    </q-tooltip>
                  </q-icon>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>

    <div class="col-12 col-md-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6
            class="text-subtitle1 q-my-none"
            v-text="$t('lnurlp.extension_title')"
          ></h6>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <q-expansion-item
              group="extras"
              icon="swap_vertical_circle"
              :label="$t('lnurlp.api_info')"
              :content-inset-level="0.5"
            >
              <q-btn
                flat
                :label="$t('lnurlp.swagger_api')"
                type="a"
                href="../docs#/lnurlp"
              ></q-btn>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                :label="$t('lnurlp.list_pay_links')"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-blue">GET</span>
                      /lnurlp/api/v1/links</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;invoice_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 200 OK (application/json)
                    </h5>
                    <code>[&lt;pay_link_object&gt;, ...]</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X GET <span v-text="baseUrl"></span> -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].inkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                :label="$t('lnurlp.get_pay_link')"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-blue">GET</span>
                      /lnurlp/api/v1/links/&lt;pay_id&gt;</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;invoice_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 201 CREATED (application/json)
                    </h5>
                    <code>{"lnurl": &lt;string&gt;}</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X GET
                      <span v-text="baseUrl + '/&lt;pay_id&gt;'"></span>
                      -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].inkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                :label="$t('lnurlp.create_a_pay_link')"
              >
                <q-btn
                  flat
                  :label="$t('lnurlp.swagger_api')"
                  type="a"
                  href="../docs#/lnurlp"
                ></q-btn>
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-green">POST</span>
                      /lnurlp/api/v1/links</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <code
                      >{"description": &lt;string&gt; "amount": &lt;integer&gt;
                      "max": &lt;integer&gt; "min": &lt;integer&gt;
                      "comment_chars": &lt;integer&gt; "username":
                      &lt;string&gt; }</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 201 CREATED (application/json)
                    </h5>
                    <code>{"lnurl": &lt;string&gt;}</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X POST <span v-text="baseUrl"></span> -d
                      '{"description": &lt;string&gt;, "amount":
                      &lt;integer&gt;, "max": &lt;integer&gt;, "min":
                      &lt;integer&gt;, "comment_chars": &lt;integer&gt;}' -H
                      "Content-type: application/json" -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                :label="$t('lnurlp.update_a_pay_link')"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-green">PUT</span>
                      /lnurlp/api/v1/links/&lt;pay_id&gt;</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Body (application/json)
                    </h5>
                    <code
                      >{"description": &lt;string&gt;, "amount":
                      &lt;integer&gt;}</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 200 OK (application/json)
                    </h5>
                    <code>{"lnurl": &lt;string&gt;}</code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X PUT
                      <span v-text="baseUrl + '/&lt;pay_id&gt;'"></span>
                      -d '{"description": &lt;string&gt;, "amount":
                      &lt;integer&gt;}' -H "Content-type: application/json" -H
                      "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                :label="$t('lnurlp.delete_a_pay_link')"
                class="q-pb-md"
              >
                <q-card>
                  <q-card-section>
                    <code
                      ><span class="text-pink">DELETE</span>
                      /lnurlp/api/v1/links/&lt;pay_id&gt;</code
                    >
                    <h5 class="text-caption q-mt-sm q-mb-none">Headers</h5>
                    <code>{"X-Api-Key": &lt;admin_key&gt;}</code><br />
                    <h5 class="text-caption q-mt-sm q-mb-none">
                      Returns 204 NO CONTENT
                    </h5>
                    <code></code>
                    <h5 class="text-caption q-mt-sm q-mb-none">Curl example</h5>
                    <code
                      >curl -X DELETE
                      <span v-text="baseUrl + '/&lt;pay_id&gt;'"></span>
                      -H "X-Api-Key:
                      <span v-text="g.user.wallets[0].adminkey"></span>"
                    </code>
                  </q-card-section>
                </q-card>
              </q-expansion-item>
            </q-expansion-item>
            <q-separator></q-separator>
            <q-expansion-item
              group="extras"
              icon="info"
              :label="$t('lnurlp.powered_by_lnurl')"
            >
              <q-card>
                <q-card-section>
                  <p>
                    <b v-text="$t('lnurlp.https_warning')"></b><br />
                    <span v-text="$t('lnurlp.lnurl_description')"></span>
                  </p>
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

    <q-dialog v-model="formDialog.show" @hide="closeFormDialog">
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="sendFormData" class="q-gutter-md">
          <q-select
            filled
            dense
            emit-value
            v-model="formDialog.data.wallet"
            :options="g.user.walletOptions"
            :label="$t('lnurlp.wallet_label')"
          >
          </q-select>
          <q-input
            filled
            dense
            v-model.trim="formDialog.data.description"
            type="text"
            :label="$t('lnurlp.item_description')"
          >
          </q-input>
          <div class="row">
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.username"
                type="text"
                :label="$t('lnurlp.lightning_address')"
                @input="
                  formDialog.data.username =
                    formDialog.data.username.toLowerCase()
                "
              />
            </div>
            <div class="col" style="flex: 0 0 auto; margin-top: 10px">
              <span class="label"> &nbsp;@&nbsp; </span>
            </div>
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.domain"
                type="text"
                :label="domain"
              />
            </div>
          </div>
          <div class="row q-col-gutter-sm q-mx-sm">
            <q-input
              filled
              dense
              v-model.number="formDialog.data.min"
              type="number"
              :step="
                formDialog.data.currency &&
                formDialog.data.currency !== 'satoshis'
                  ? '0.01'
                  : '1'
              "
              :label="
                formDialog.fixedAmount
                  ? $t('lnurlp.amount_label')
                  : $t('lnurlp.min_label')
              "
              :hint="
                formDialog.data.currency &&
                fiatRates[formDialog.data.currency] &&
                formDialog.data.min
                  ? $t('lnurlp.approx_sats', {
                      sats: parseInt(
                        Math.round(
                          formDialog.data.min *
                            fiatRates[formDialog.data.currency]
                        )
                      )
                    })
                  : ''
              "
            ></q-input>
            <q-input
              v-if="!formDialog.fixedAmount"
              filled
              dense
              v-model.number="formDialog.data.max"
              type="number"
              :step="
                formDialog.data.currency &&
                formDialog.data.currency !== 'satoshis'
                  ? '0.01'
                  : '1'
              "
              :label="$t('lnurlp.max_label')"
              :hint="
                formDialog.data.currency &&
                fiatRates[formDialog.data.currency] &&
                formDialog.data.max
                  ? $t('lnurlp.approx_sats', {
                      sats: parseInt(
                        Math.round(
                          formDialog.data.max *
                            fiatRates[formDialog.data.currency]
                        )
                      )
                    })
                  : ''
              "
            ></q-input>
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col">
              <q-checkbox
                dense
                v-model="formDialog.fixedAmount"
                :label="$t('lnurlp.fixed_amount')"
              />
            </div>
            <div class="col">
              <q-select
                dense
                :options="g.allowedCurrencies || g.currencies"
                v-model="formDialog.data.currency"
                :display-value="formDialog.data.currency || 'satoshis'"
                :label="$t('currency')"
                :hint="
                  $t('lnurlp.currency_hint') +
                  (formDialog.data.currency &&
                  fiatRates[formDialog.data.currency]
                    ? ' ' +
                      $t('lnurlp.currency_rate', {
                        currency: formDialog.data.currency,
                        rate: fiatRates[formDialog.data.currency]
                      })
                    : '')
                "
                @input="updateFiatRate"
              />
            </div>
          </div>
          <q-expansion-item
            group="advanced"
            icon="settings"
            :label="$t('lnurlp.advanced_options')"
          >
            <q-card>
              <q-card-section>
                <h5
                  class="text-caption q-mt-sm q-mb-none"
                  v-text="$t('lnurlp.lud11_title')"
                ></h5>
                <div class="row">
                  <div class="col-12">
                    <q-checkbox
                      dense
                      :toggle-indeterminate="false"
                      v-model="formDialog.data.disposable"
                      :label="$t('lnurlp.disposable_label')"
                    />
                  </div>
                </div>
                <h5
                  class="text-caption q-mt-sm q-mb-none"
                  v-text="$t('lnurlp.lnurl_section')"
                ></h5>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model.number="formDialog.data.comment_chars"
                      type="number"
                      :label="$t('lnurlp.comment_chars_label')"
                      :hint="$t('lnurlp.comment_chars_hint')"
                    >
                    </q-input>
                  </div>
                </div>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_url"
                      type="text"
                      :label="$t('lnurlp.webhook_url_label')"
                      :hint="$t('lnurlp.webhook_url_hint')"
                    ></q-input>
                  </div>
                </div>
                <div class="row" v-if="formDialog.data.webhook_url">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_headers"
                      type="text"
                      :label="$t('lnurlp.webhook_headers_label')"
                      :hint="$t('lnurlp.webhook_headers_hint')"
                    ></q-input>
                  </div>
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_body"
                      type="text"
                      :label="$t('lnurlp.webhook_body_label')"
                      :hint="$t('lnurlp.webhook_body_hint')"
                    ></q-input>
                  </div>
                </div>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.success_text"
                      type="text"
                      :label="$t('lnurlp.success_text_label')"
                      :hint="$t('lnurlp.success_text_hint')"
                    ></q-input>
                  </div>
                </div>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.success_url"
                      type="text"
                      :label="$t('lnurlp.success_url_label')"
                      :hint="$t('lnurlp.success_url_hint')"
                    >
                    </q-input>
                  </div>
                </div>
              </q-card-section>
              <q-card-section>
                <h5
                  class="text-caption q-mt-sm q-mb-none"
                  v-text="$t('lnurlp.nostr_section')"
                ></h5>
                <div class="row">
                  <div class="col-12">
                    <q-checkbox
                      :toggle-indeterminate="false"
                      dense
                      v-model="formDialog.data.zaps"
                      :label="$t('lnurlp.enable_zaps')"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>
          </q-expansion-item>
          <div class="row q-mt-lg">
            <q-btn
              v-if="formDialog.data.id"
              unelevated
              color="primary"
              type="submit"
              :label="$t('lnurlp.update_pay_link')"
            ></q-btn>
            <q-btn
              v-else
              unelevated
              color="primary"
              :disable="
                formDialog.data.wallet == null ||
                formDialog.data.description == null ||
                formDialog.data.min == null ||
                formDialog.data.min <= 0
              "
              type="submit"
              :label="$t('lnurlp.create_pay_link')"
            ></q-btn>
            <q-btn
              v-close-popup
              flat
              color="grey"
              class="q-ml-auto"
              :label="$t('cancel')"
            ></q-btn>
          </div>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog v-model="qrCodeDialog.show" position="top">
      <q-card v-if="qrCodeDialog.data" class="q-pa-lg lnbits__dialog-card">
        <lnbits-qrcode-lnurl :url="activeUrl" :nfc="true"></lnbits-qrcode-lnurl>
        <p style="word-break: break-all">
          <strong v-text="$t('lnurlp.id_label')"></strong>
          <span v-text="qrCodeDialog.data.id"></span><br />
          <strong v-text="$t('lnurlp.amount_label_colon')"></strong>
          <span v-text="qrCodeDialog.data.amount"></span><br />

          <span v-if="qrCodeDialog.data.currency">
            <strong
              v-text="
                $t('lnurlp.currency_price', {
                  currency: qrCodeDialog.data.currency
                })
              "
            ></strong>
            <span
              v-if="fiatRates[qrCodeDialog.data.currency]"
              v-text="fiatRates[qrCodeDialog.data.currency] + 'sat'"
            ></span>
            <span v-else v-text="$t('lnurlp.loading')"></span>
            <br />
          </span>
          <strong v-text="$t('lnurlp.accepts_comments')"></strong>
          <span v-text="qrCodeDialog.data.comments"></span><br />
          <strong v-text="$t('lnurlp.dispatches_webhook')"></strong>
          <span v-text="qrCodeDialog.data.webhook"></span><br />
          <strong v-text="$t('lnurlp.on_success_label')"></strong>
          <span v-text="qrCodeDialog.data.success"></span><br />
          <span v-if="qrCodeDialog.data.username">
            <strong v-text="$t('lnurlp.lightning_address_label')"></strong>
            <span v-text="lnaddress(qrCodeDialog.data)"></span>
            <q-icon
              name="content_copy"
              class="text-grey cursor-pointer q-ml-sm"
              @click="utils.copyText(lnaddress(qrCodeDialog.data))"
            ></q-icon>
            <q-icon name="qr_code" class="text-grey cursor-pointer q-ml-sm">
              <q-popup-proxy>
                <lnbits-qrcode
                  class="q-pa-md"
                  :value="lnaddress(qrCodeDialog.data)"
                  :show-buttons="false"
                ></lnbits-qrcode>
              </q-popup-proxy>
            </q-icon>
            <br />
          </span>
        </p>
        <div class="row q-mt-lg q-gutter-sm">
          <q-btn
            outline
            color="grey"
            icon="link"
            @click="
              utils.copyText(
                qrCodeDialog.data.pay_url,
                'Link copied to clipboard!'
              )
            "
          >
            <q-tooltip>
              <span v-text="$t('lnurlp.copy_link')"></span>
            </q-tooltip>
          </q-btn>
          <q-btn
            v-close-popup
            flat
            color="grey"
            class="q-ml-auto"
            :label="$t('close')"
          ></q-btn>
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>
