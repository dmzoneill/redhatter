function login (context, sendResponse) {
  chrome.storage.sync.get('headless', (result) => {
    const headless = result.headless?.toString() || 'false'
    const url = `http://localhost:8009/get_creds?context=${context}&headless=${headless}`

    console.log(`🔑 Fetching credentials from: ${url}`)

    fetch(url)
      .then(response => {
        if (!response.ok) throw new Error('HTTP error ' + response.status)
        return response.text()
      })
      .then(data => {
        console.log('✅ Credentials received, storing...')
        chrome.storage.sync.set({ creds: data }, () => {
          sendResponse('done')
        })
      })
      .catch(error => {
        console.error('❌ Error fetching credentials:', error)
        sendResponse('error')
      })
  })

  // Necessary for async sendResponse
  return true
}

function getEmail (sendResponse) {
  const url = 'http://localhost:8009/get_associate_email'

  console.log(`🔑 Fetching associate email from: ${url}`)

  fetch(url)
    .then(response => {
      if (!response.ok) throw new Error('HTTP error ' + response.status)
      return response.text()
    })
    .then(data => {
      console.log('✅ Email received, storing...')
      chrome.storage.sync.set({ email: data }, () => {
        sendResponse('done')
      })
    })
    .catch(error => {
      console.error('❌ Error fetching email:', error)
      sendResponse('error')
    })

  // Necessary for async sendResponse
  return true
}

// Background message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('📨 Received message:', message)

  if (message.action === 'doAutomaticLogin' || message.action === 'doOpenEphemeral') {
    return login(message.context, sendResponse)
  }

  if (message.action === 'DoGetAssociateEmail') {
    return getEmail(sendResponse)
  }

  return false
})
