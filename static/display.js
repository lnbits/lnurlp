window.PageLnurlpPublic = {
  template: '#page-lnurlp-public',
  data() {
    return {
      url: '',
      payLink: null
    }
  },
  methods: {
    setUrl(link_id, domain) {
      this.url = `https://${domain || window.location.host}/lnurlp/${link_id}`
    },
    getPayLink() {
      this.api
        .request('GET', `/lnurlp/api/v1/links/public/${this.$route.params.id}`)
        .then(res => {
          this.payLink = res.data
          this.setUrl(this.payLink.id, this.payLink.domain)
        })
        .catch(this.utils.notifyApiError)
    }
  },
  created() {
    this.setUrl(this.$route.params.id)
    this.getPayLink()
  }
}
