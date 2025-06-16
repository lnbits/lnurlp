/* globals Quasar, Vue, _, VueQrcode, windowMixin, LNbits, LOCALE */

const locationPath = [
  window.location.protocol,
  '//',
  window.location.host,
  window.location.pathname
].join('')

const mapPayLink = obj => {
  obj._data = _.clone(obj)
  obj.created_at = LNbits.utils.formatDateString(obj.created_at)
  obj.updated_at = LNbits.utils.formatDateString(obj.updated_at)

  obj.print_url = [locationPath, 'print/', obj.id].join('')
  obj.pay_url = [locationPath, 'link/', obj.id].join('')
  
  // Store warning for display
  obj.hasWarning = !!obj.warning
  obj.warningMessage = obj.warning || ''
  
  return obj
}

window.app = Vue.createApp({
  el: '#vue',
  mixins: [window.windowMixin],
  computed: {
    endpoint: function () {
      return `/lnurlp/api/v1/settings?usr=${this.g.user.id}`
    },
    showUrlWarning: function () {
      const protocol = window.location.protocol
      const hostname = window.location.hostname
      
      // Don't show warning for HTTPS
      if (protocol === 'https:') return false
      
      // Don't show warning for Tor onion addresses
      if (hostname.endsWith('.onion')) return false
      
      // Show warning for everything else (HTTP, localhost, etc.)
      return true
    },
    urlWarningMessage: function () {
      const hostname = window.location.hostname
      
      if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
        return 'You are accessing this page via localhost. LNURL pay links created here will only work locally and may not work with external wallets.'
      } else if (hostname.match(/^192\.168\.|^10\.|^172\.(1[6-9]|2[0-9]|3[01])\./)) {
        return `You are accessing this page via an internal IP address (${hostname}). LNURL pay links created here will only work within your local network.`
      } else if (hostname.endsWith('.local')) {
        return `You are accessing this page via a local network address (${hostname}). LNURL pay links may not work with external wallets.`
      } else {
        return 'You are accessing this page via HTTP (not HTTPS). LNURL pay links created here may not work with most wallets. Use HTTPS or Tor onion addresses for best compatibility.'
      }
    }
  },
  data() {
    return {
      settings: [
        {
          type: 'str',
          description: 'Nostr private key used to zap',
          name: 'nostr_private_key'
        }
      ],
      domain: window.location.host,
      currencies: [],
      fiatRates: {},
      payLinks: [],
      payLinksTable: {
        columns: [
          {
            name: 'created_at',
            label: 'Created',
            align: 'left',
            field: 'created_at',
            sortable: true
          },
          {
            name: 'description',
            label: 'Description',
            align: 'left',
            field: 'description'
          },
          {
            name: 'amount',
            label: 'Amount',
            align: 'left',
            format: (_, row) => {
              const min = row.min
              const max = row.max
              if (min === max) return `${min}`
              return `${min} - ${max}`
            }
          },
          {
            name: 'currency',
            label: 'Currency',
            align: 'left',
            field: 'currency',
            format: val => val ?? 'sat'
          },
          {
            name: 'username',
            label: 'Username',
            align: 'left',
            field: 'username',
            sortable: true,
            format: val => val ?? 'None',
            classes: val => (val ? 'text-normal' : 'text-grey')
          }
        ],
        pagination: {
          rowsPerPage: 10
        }
      },
      nfcTagWriting: false,
      formDialog: {
        show: false,
        fixedAmount: true,
        data: {
          zaps: false
        }
      },
      qrCodeDialog: {
        show: false,
        data: null
      }
    }
  },
  methods: {
    getPayLinks() {
      LNbits.api
        .request(
          'GET',
          '/lnurlp/api/v1/links?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.payLinks = response.data.map(mapPayLink)
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    closeFormDialog() {
      this.resetFormData()
    },
    openQrCodeDialog(linkId) {
      var link = _.findWhere(this.payLinks, {id: linkId})
      if (link.currency) this.updateFiatRate(link.currency)

      this.qrCodeDialog.data = {
        id: link.id,
        amount:
          (link.min === link.max ? link.min : `${link.min} - ${link.max}`) +
          ' ' +
          (link.currency || 'sat'),
        currency: link.currency,
        comments: link.comment_chars
          ? `${link.comment_chars} characters`
          : 'no',
        webhook: link.webhook_url || 'nowhere',
        success:
          link.success_text || link.success_url
            ? 'Display message "' +
              link.success_text +
              '"' +
              (link.success_url ? ' and URL "' + link.success_url + '"' : '')
            : 'do nothing',
        lnurl: link.lnurl,
        pay_url: link.pay_url,
        print_url: link.print_url,
        username: link.username
      }
      this.qrCodeDialog.show = true
    },
    openUpdateDialog(linkId) {
      const link = _.findWhere(this.payLinks, {id: linkId})
      if (link.currency) this.updateFiatRate(link.currency)

      this.formDialog.data = _.clone(link._data)
      this.formDialog.show = true
      this.formDialog.fixedAmount =
        this.formDialog.data.min === this.formDialog.data.max
    },
    sendFormData() {
      const wallet = _.findWhere(this.g.user.wallets, {
        id: this.formDialog.data.wallet
      })
      const data = _.clone(this.formDialog.data)
      if (this.formDialog.fixedAmount) data.max = data.min
      if (data.currency === 'satoshis') data.currency = null
      if (isNaN(parseInt(data.comment_chars))) data.comment_chars = 0
      if (data.id) {
        this.updatePayLink(wallet, data)
      } else {
        this.createPayLink(wallet, data)
      }
    },
    resetFormData() {
      this.formDialog = {
        show: false,
        fixedAmount: true,
        data: {}
      }
    },
    updatePayLink(wallet, data) {
      LNbits.api
        .request(
          'PUT',
          '/lnurlp/api/v1/links/' + data.id,
          wallet.adminkey,
          data
        )
        .then(response => {
          this.payLinks = _.reject(this.payLinks, obj => obj.id === data.id)
          this.payLinks.push(mapPayLink(response.data))
          this.formDialog.show = false
          this.resetFormData()
          // Show warning if present
          if (response.data.warning) {
            this.$q.notify({
              type: 'warning',
              message: `Pay link updated with warning: ${response.data.warning}`,
              timeout: 8000,
              actions: [{icon: 'close', color: 'white'}]
            })
          }
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    createPayLink(wallet, data) {
      LNbits.api
        .request('POST', '/lnurlp/api/v1/links', wallet.adminkey, data)
        .then(response => {
          this.getPayLinks()
          this.formDialog.show = false
          this.resetFormData()
          // Show warning if present
          if (response.data.warning) {
            this.$q.notify({
              type: 'warning',
              message: `Pay link created with warning: ${response.data.warning}`,
              timeout: 8000,
              actions: [{icon: 'close', color: 'white'}]
            })
          }
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    deletePayLink(linkId) {
      var link = _.findWhere(this.payLinks, {id: linkId})

      LNbits.utils
        .confirmDialog('Are you sure you want to delete this pay link?')
        .onOk(() => {
          LNbits.api
            .request(
              'DELETE',
              '/lnurlp/api/v1/links/' + linkId,
              _.findWhere(this.g.user.wallets, {id: link.wallet}).adminkey
            )
            .then(() => {
              this.payLinks = _.reject(this.payLinks, obj => obj.id === linkId)
            })
            .catch(err => {
              LNbits.utils.notifyApiError(err)
            })
        })
    },
    updateFiatRate(currency) {
      LNbits.api
        .request('GET', '/lnurlp/api/v1/rate/' + currency, null)
        .then(response => {
          let rates = _.clone(this.fiatRates)
          rates[currency] = response.data.rate
          this.fiatRates = rates
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    },
    writeNfcTag: async function (lnurl) {
      try {
        if (typeof NDEFReader == 'undefined') {
          throw {
            toString: function () {
              return 'NFC not supported on this device or browser.'
            }
          }
        }

        const ndef = new NDEFReader()

        this.nfcTagWriting = true
        this.$q.notify({
          message: 'Tap your NFC tag to write the LNURL-pay link to it.'
        })

        await ndef.write({
          records: [{recordType: 'url', data: 'lightning:' + lnurl, lang: 'en'}]
        })

        this.nfcTagWriting = false
        this.$q.notify({
          type: 'positive',
          message: 'NFC tag written successfully.'
        })
      } catch (error) {
        this.nfcTagWriting = false
        this.$q.notify({
          type: 'negative',
          message: error
            ? error.toString()
            : 'An unexpected error has occurred.'
        })
      }
    }
  },
  created() {
    if (this.g.user.wallets?.length) {
      this.getPayLinks()
    }
    LNbits.api
      .request('GET', '/lnurlp/api/v1/currencies')
      .then(response => {
        this.currencies = ['satoshis', ...response.data]
      })
      .catch(err => {
        LNbits.utils.notifyApiError(err)
      })
  }
})
