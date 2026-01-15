window.PageLnurlp = {
  template: '#page-lnurlp',
  computed: {
    baseUrl() {
      return window.location.origin + '/lnurlp/api/v1/links'
    },
    endpoint() {
      return `/lnurlp/api/v1/settings?usr=${this.g.user.id}`
    }
  },
  data() {
    return {
      activeUrl: '',
      settings: [
        {
          type: 'str',
          description: 'Nostr private key used to zap',
          name: 'nostr_private_key'
        }
      ],
      domain: window.location.host,
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
          disposable: true,
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
    lnaddress(link) {
      const domain = link.domain || window.location.host
      return `${link.username}@${domain}`
    },
    mapPayLink(obj) {
      const locationPath = [
        window.location.protocol,
        '//',
        window.location.host,
        window.location.pathname
      ].join('')
      obj._data = _.clone(obj)
      obj.created_at = LNbits.utils.formatDate(obj.created_at)
      obj.updated_at = LNbits.utils.formatDate(obj.updated_at)
      if (obj.currency) {
        obj.min = obj.min / obj.fiat_base_multiplier
        obj.max = obj.max / obj.fiat_base_multiplier
      }
      obj.print_url = [locationPath, 'print/', obj.id].join('')
      obj.pay_url = [locationPath, 'link/', obj.id].join('')
      return obj
    },
    getPayLinks() {
      LNbits.api
        .request(
          'GET',
          '/lnurlp/api/v1/links?all_wallets=true',
          this.g.user.wallets[0].inkey
        )
        .then(response => {
          this.payLinks = response.data.map(this.mapPayLink)
        })
        .catch(LNbits.utils.notifyApiError)
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
        domain: link.domain,
        pay_url: link.pay_url,
        print_url: link.print_url,
        username: link.username
      }
      const domain = link.domain || window.location.host
      this.activeUrl = `https://${domain}/lnurlp//${link.id}`
      this.qrCodeDialog.show = true
    },
    openUpdateDialog(linkId) {
      const link = _.findWhere(this.payLinks, {id: linkId})
      if (link.currency) this.updateFiatRate(link.currency)

      this.formDialog.data = {...link}
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
          this.payLinks.push(this.mapPayLink(response.data))
          this.formDialog.show = false
          this.resetFormData()
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
        .request('GET', '/api/v1/rate/' + currency, null)
        .then(response => {
          this.fiatRates[currency] = response.data.rate
        })
        .catch(err => {
          LNbits.utils.notifyApiError(err)
        })
    }
  },
  created() {
    if (this.g.user.wallets?.length) {
      this.getPayLinks()
    }
  }
}
