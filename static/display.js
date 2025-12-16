window.PageLnurlpPublic = {
  template: '#page-lnurlp-public',
  data() {
    return {
      url: ''
    }
  },
  created() {
    this.url = window.location.origin + '/lnurlp/' + this.$route.params.id
  }
}
