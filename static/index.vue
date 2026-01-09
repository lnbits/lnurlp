<template id="page-lnurlp">
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-7 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <q-btn unelevated color="primary" @click="formDialog.show = true"
            >New pay link</q-btn
          >
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
              <h5 class="text-subtitle1 q-my-none">Pay links</h5>
            </div>
          </div>
          <q-table
            dense
            flat
            :rows="payLinks"
            :columns="payLinksTable.columns"
            row-key="id"
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
                    ><q-tooltip>Shareable Page</q-tooltip></q-btn
                  >
                  <q-btn
                    dense
                    size="xs"
                    icon="visibility"
                    :color="$q.dark.isActive ? 'grey-7' : 'grey-5'"
                    class="q-ml-sm"
                    @click="openQrCodeDialog(props.row.id)"
                    ><q-tooltip>View Link</q-tooltip></q-btn
                  >
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="openUpdateDialog(props.row.id)"
                    icon="edit"
                    color="light-blue"
                    class="q-ml-sm"
                  >
                    <q-tooltip>Edit</q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="deletePayLink(props.row.id)"
                    icon="cancel"
                    color="pink"
                    class="q-ml-sm"
                    ><q-tooltip>Delete</q-tooltip></q-btn
                  >
                </q-td>
                <q-td
                  v-for="col in props.cols"
                  :key="col.name"
                  :props="props"
                  v-text="col.value"
                ></q-td>
                <q-td>
                  <q-icon v-if="props.row.webhook_url" size="14px" name="http">
                    <q-tooltip
                      >Webhook to <span v-text="props.row.webhook_url"></span
                    ></q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.success_text || props.row.success_url"
                    size="14px"
                    name="call_to_action"
                  >
                    <q-tooltip>
                      On success, show message '<span
                        v-text="props.row.success_text"
                      ></span
                      >'
                      <span v-if="props.row.success_url"
                        >and URL '<span v-text="props.row.success_url"></span
                        >'</span
                      >
                    </q-tooltip>
                  </q-icon>
                  <q-icon
                    v-if="props.row.comment_chars > 0"
                    size="14px"
                    name="insert_comment"
                  >
                    <q-tooltip>
                      <span v-text="props.row.comment_chars"></span>-char
                      comment allowed
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
          <h6 class="text-subtitle1 q-my-none">LNURL-pay extension</h6>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <q-expansion-item
              group="extras"
              icon="swap_vertical_circle"
              label="API info"
              :content-inset-level="0.5"
            >
              <q-btn
                flat
                label="Swagger API"
                type="a"
                href="../docs#/lnurlp"
              ></q-btn>
              <q-expansion-item
                group="api"
                dense
                expand-separator
                label="List pay links"
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
                label="Get a pay link"
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
                label="Create a pay link"
              >
                <q-btn
                  flat
                  label="Swagger API"
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
                label="Update a pay link"
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
                label="Delete a pay link"
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
              label="Powered by LNURL"
            >
              <q-card>
                <q-card-section>
                  <p>
                    <b>WARNING: LNURL must be used over https or TOR</b><br />
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

    <q-dialog v-model="formDialog.show" @hide="closeFormDialog">
      <q-card class="q-pa-lg q-pt-xl lnbits__dialog-card">
        <q-form @submit="sendFormData" class="q-gutter-md">
          <q-select
            filled
            dense
            emit-value
            v-model="formDialog.data.wallet"
            :options="g.user.walletOptions"
            label="Wallet *"
          >
          </q-select>
          <q-input
            filled
            dense
            v-model.trim="formDialog.data.description"
            type="text"
            label="Item description *"
          >
          </q-input>
          <div class="row">
            <div class="col">
              <q-input
                filled
                dense
                v-model.trim="formDialog.data.username"
                type="text"
                label="Lightning Address"
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
              :label="formDialog.fixedAmount ? 'Amount *' : 'Min *'"
              :hint="
                formDialog.data.currency &&
                fiatRates[formDialog.data.currency] &&
                formDialog.data.min
                  ? `approx. ${parseInt(Math.round(formDialog.data.min * fiatRates[formDialog.data.currency]))} sat`
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
              label="Max *"
              :hint="
                formDialog.data.currency &&
                fiatRates[formDialog.data.currency] &&
                formDialog.data.max
                  ? `approx. ${parseInt(Math.round(formDialog.data.max * fiatRates[formDialog.data.currency]))} sat`
                  : ''
              "
            ></q-input>
          </div>
          <div class="row q-col-gutter-sm">
            <div class="col">
              <q-checkbox
                dense
                v-model="formDialog.fixedAmount"
                label="Fixed amount"
              />
            </div>
            <div class="col">
              <q-select
                dense
                :options="g.allowedCurrencies || g.currencies"
                v-model="formDialog.data.currency"
                :display-value="formDialog.data.currency || 'satoshis'"
                label="Currency"
                :hint="
                  'Converted to satoshis at each payment. ' +
                  (formDialog.data.currency &&
                  fiatRates[formDialog.data.currency]
                    ? `Currently 1 ${formDialog.data.currency} = ${fiatRates[formDialog.data.currency]} sat`
                    : '')
                "
                @input="updateFiatRate"
              />
            </div>
          </div>
          <q-expansion-item
            group="advanced"
            icon="settings"
            label="Advanced options"
          >
            <q-card>
              <q-card-section>
                <h5 class="text-caption q-mt-sm q-mb-none">
                  LUD-11: Disposable and storeable payRequests.
                </h5>
                <div class="row">
                  <div class="col-12">
                    <q-checkbox
                      dense
                      :toggle-indeterminate="false"
                      v-model="formDialog.data.disposable"
                      label="If enabled, the LNURL will not be stored (default)."
                    />
                  </div>
                </div>
                <h5 class="text-caption q-mt-sm q-mb-none">LNURL</h5>
                <div class="row">
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model.number="formDialog.data.comment_chars"
                      type="number"
                      label="Comment maximum characters"
                      hint="Allow the payer to attach a comment."
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
                      label="Webhook URL (optional)"
                      hint="A URL to be called whenever this link receives a payment."
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
                      label="Webhook headers (optional)"
                      hint="Custom data as JSON string, send headers along with the webhook."
                    ></q-input>
                  </div>
                  <div class="col-12">
                    <q-input
                      filled
                      dense
                      v-model="formDialog.data.webhook_body"
                      type="text"
                      label="Webhook custom data (optional)"
                      hint="Custom data as JSON string, will get posted along with webhook 'body' field."
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
                      label="Success message (optional)"
                      hint="Will be shown to the user in his wallet after a successful payment."
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
                      label="Success URL (optional)"
                      hint="Link will be shown to the sender after a successful payment."
                    >
                    </q-input>
                  </div>
                </div>
              </q-card-section>
              <q-card-section>
                <h5 class="text-caption q-mt-sm q-mb-none">Nostr</h5>
                <div class="row">
                  <div class="col-12">
                    <q-checkbox
                      :toggle-indeterminate="false"
                      dense
                      v-model="formDialog.data.zaps"
                      label="Enable nostr zaps"
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
              >Update pay link</q-btn
            >
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
              >Create pay link</q-btn
            >
            <q-btn v-close-popup flat color="grey" class="q-ml-auto"
              >Cancel</q-btn
            >
          </div>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog v-model="qrCodeDialog.show" position="top">
      <q-card v-if="qrCodeDialog.data" class="q-pa-lg lnbits__dialog-card">
        <lnbits-qrcode-lnurl :url="activeUrl" :nfc="true"></lnbits-qrcode-lnurl>
        <p style="word-break: break-all">
          <strong>ID:</strong> <span v-text="qrCodeDialog.data.id"></span><br />
          <strong>Amount:</strong>
          <span v-text="qrCodeDialog.data.amount"></span><br />

          <span v-if="qrCodeDialog.data.currency"
            ><strong
              ><span v-text="qrCodeDialog.data.currency"></span> price:</strong
            >
            <span
              v-if="fiatRates[qrCodeDialog.data.currency]"
              v-text="fiatRates[qrCodeDialog.data.currency] + 'sat'"
            ></span>
            <span v-else>Loading...</span>
            <br
          /></span>
          <strong>Accepts comments:</strong>
          <span v-text="qrCodeDialog.data.comments"></span><br />
          <strong>Dispatches webhook to:</strong>
          <span v-text="qrCodeDialog.data.webhook"></span><br />
          <strong>On success:</strong>
          <span v-text="qrCodeDialog.data.success"></span><br />
          <span v-if="qrCodeDialog.data.username">
            <strong>Lightning Address: </strong>
            <span v-text="lnaddress(qrCodeDialog.data)"></span>
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
            ><q-tooltip>Copy sharable link</q-tooltip>
          </q-btn>
          <q-btn v-close-popup flat color="grey" class="q-ml-auto">Close</q-btn>
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>
