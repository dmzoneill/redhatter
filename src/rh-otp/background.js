// Get auth token from native host
function getAuthToken () {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendNativeMessage('com.redhat.rhotp', { action: 'get_token' }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('❌ Native messaging error:', chrome.runtime.lastError)
        reject(new Error(chrome.runtime.lastError.message))
        return
      }
      if (response && response.success && response.token) {
        resolve(response.token)
      } else {
        reject(new Error(response?.error || 'Failed to get auth token'))
      }
    })
  })
}

function login (context, sendResponse) {
  chrome.storage.sync.get('headless', async (result) => {
    try {
      const headless = result.headless?.toString() || 'false'
      const url = `http://localhost:8009/get_creds?context=${context}&headless=${headless}`

      console.log(`🔑 Fetching credentials from: ${url}`)

      // Get auth token
      const token = await getAuthToken()

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })

      if (!response.ok) throw new Error('HTTP error ' + response.status)

      const data = await response.text()
      console.log('✅ Credentials received, storing...')
      chrome.storage.sync.set({ creds: data }, () => {
        sendResponse('done')
      })
    } catch (error) {
      console.error('❌ Error fetching credentials:', error)
      sendResponse('error')
    }
  })

  // Necessary for async sendResponse
  return true
}

async function getEmail (sendResponse) {
  const url = 'http://localhost:8009/get_associate_email'

  console.log(`🔑 Fetching associate email from: ${url}`)

  try {
    // Get auth token
    const token = await getAuthToken()

    const response = await fetch(url, {
      headers: {
        Authorization: `Bearer ${token}`
      }
    })

    if (!response.ok) throw new Error('HTTP error ' + response.status)

    const data = await response.text()
    console.log('✅ Email received, storing...')
    chrome.storage.sync.set({ email: data }, () => {
      sendResponse('done')
    })
  } catch (error) {
    console.error('❌ Error fetching email:', error)
    sendResponse('error')
  }

  // Necessary for async sendResponse
  return true
}

// Background message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('📨 Received message:', message)

  if (message.action === 'getAuthToken') {
    // Handle token requests from popup
    getAuthToken()
      .then(token => sendResponse({ success: true, token }))
      .catch(error => sendResponse({ success: false, error: error.message }))
    return true // Keep channel open for async response
  }

  if (message.action === 'doAutomaticLogin' || message.action === 'doOpenEphemeral') {
    return login(message.context, sendResponse)
  }

  if (message.action === 'DoGetAssociateEmail') {
    return getEmail(sendResponse)
  }

  return false
})
