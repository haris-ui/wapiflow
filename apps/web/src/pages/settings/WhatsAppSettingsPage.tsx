import React, { useState } from 'react'
import {
  useWhatsAppConfig,
  useConnectWhatsApp,
  useDisconnectWhatsApp,
  useSendTestMessage,
} from '@/hooks/useWhatsApp'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import {
  MessageSquare,
  AlertCircle,
  Copy,
  Check,
  Send,
  Unlink,
  Phone,
  ShieldCheck,
} from 'lucide-react'

export default function WhatsAppSettingsPage() {
  const { data: config, isLoading, refetch } = useWhatsAppConfig()
  const connectMutation = useConnectWhatsApp()
  const disconnectMutation = useDisconnectWhatsApp()
  const testMessageMutation = useSendTestMessage()

  // Connect form state
  const [wabaId, setWabaId] = useState('')
  const [appId, setAppId] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [connectError, setConnectError] = useState<string | null>(null)
  const [connectSuccess, setConnectSuccess] = useState<string | null>(null)

  // Test message state
  const [testPhone, setTestPhone] = useState('')
  const [testText, setTestText] = useState('Hello from WapiFlow! Your WhatsApp integration is working.')
  const [testResult, setTestResult] = useState<any>(null)
  const [testError, setTestError] = useState<string | null>(null)

  // Copy helper
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const handleConnect = async (e: React.FormEvent) => {
    e.preventDefault()
    setConnectError(null)
    setConnectSuccess(null)

    try {
      await connectMutation.mutateAsync({
        waba_id: wabaId.trim(),
        app_id: appId.trim(),
        access_token: accessToken.trim(),
        phone_numbers: phoneNumber.trim()
          ? [
              {
                phone_number: phoneNumber.trim(),
                display_name: displayName.trim() || undefined,
                is_primary: true,
              },
            ]
          : undefined,
      })
      setConnectSuccess('WhatsApp Business Account connected successfully!')
      setAccessToken('')
      refetch()
    } catch (err: any) {
      setConnectError(err.message || 'Failed to connect WhatsApp account.')
    }
  }

  const handleDisconnect = async () => {
    if (!window.confirm('Are you sure you want to disconnect this WhatsApp Business Account?')) {
      return
    }
    try {
      await disconnectMutation.mutateAsync()
      refetch()
    } catch (err: any) {
      alert(err.message || 'Failed to disconnect')
    }
  }

  const handleSendTest = async (e: React.FormEvent) => {
    e.preventDefault()
    setTestError(null)
    setTestResult(null)

    if (!testPhone.trim()) {
      setTestError('Please provide a destination phone number in E.164 format (+1...)')
      return
    }

    try {
      const res = await testMessageMutation.mutateAsync({
        to_phone: testPhone.trim(),
        message_text: testText.trim(),
      })
      setTestResult(res)
    } catch (err: any) {
      setTestError(err.message || 'Failed to send test message via Meta API.')
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner size="lg" className="text-primary-600" />
      </div>
    )
  }

  const isConnected = config?.status === 'connected'

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <MessageSquare className="h-6 w-6 text-primary-600" />
          WhatsApp Cloud API Integration
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Connect your Meta WhatsApp Business Account (WABA) to send and receive real-time customer orders and messages.
        </p>
      </div>

      {/* 1. Account Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle>Account Status</CardTitle>
              <CardDescription>Current connection status with Meta WhatsApp Cloud API</CardDescription>
            </div>
            <Badge
              variant={isConnected ? 'delivered' : 'cancelled'}
              className="px-3 py-1 text-xs uppercase font-semibold"
            >
              {config?.status || 'disconnected'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          {isConnected ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-100">
                <div>
                  <span className="text-xs font-semibold uppercase text-slate-400">WABA ID</span>
                  <p className="text-sm font-mono font-medium text-slate-800">{config?.waba_id}</p>
                </div>
                <div>
                  <span className="text-xs font-semibold uppercase text-slate-400">Meta App ID</span>
                  <p className="text-sm font-mono font-medium text-slate-800">{config?.app_id}</p>
                </div>
              </div>

              {/* Phone Numbers */}
              <div>
                <span className="text-xs font-semibold uppercase text-slate-400 mb-2 block">
                  Configured Phone Numbers
                </span>
                {config?.phone_numbers && config.phone_numbers.length > 0 ? (
                  <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
                    {config.phone_numbers.map((phone) => (
                      <div key={phone.id} className="p-3 flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2.5">
                          <div className="p-1.5 bg-primary-50 rounded-md text-primary-600">
                            <Phone className="h-4 w-4" />
                          </div>
                          <div>
                            <span className="font-semibold text-slate-900">{phone.phone_number}</span>
                            {phone.display_name && (
                              <span className="text-xs text-slate-500 ml-2">({phone.display_name})</span>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {phone.quality_rating && (
                            <Badge variant="ready">
                              {phone.quality_rating}
                            </Badge>
                          )}
                          {phone.is_primary && (
                            <Badge variant="delivered">
                              Primary
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No phone numbers configured yet.</p>
                )}
              </div>

              <div className="flex justify-end pt-2">
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleDisconnect}
                  isLoading={disconnectMutation.isPending}
                  className="flex items-center gap-1.5"
                >
                  <Unlink className="h-4 w-4" />
                  Disconnect WABA
                </Button>
              </div>
            </div>
          ) : (
            <div className="p-6 text-center bg-slate-50 rounded-xl border border-dashed border-slate-200">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400 mb-2">
                <AlertCircle className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-800">No WhatsApp Account Connected</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-4">
                Connect your Meta WhatsApp Cloud API credentials below to start receiving webhook messages and sending order updates.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Connect / Reconnect Credentials */}
      <Card>
        <CardHeader>
          <CardTitle>{isConnected ? 'Update Credentials' : 'Connect Meta WABA'}</CardTitle>
          <CardDescription>
            Enter your Meta App ID, WhatsApp Business Account ID, and System User Token from Meta Developers Console.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleConnect} className="space-y-4">
            {connectError && (
              <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                {connectError}
              </div>
            )}
            {connectSuccess && (
              <div className="p-3 text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg">
                {connectSuccess}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="wabaId">WhatsApp Business Account ID (WABA ID) *</Label>
                <Input
                  id="wabaId"
                  placeholder="e.g. 100652245..."
                  value={wabaId}
                  onChange={(e) => setWabaId(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="appId">Meta App ID *</Label>
                <Input
                  id="appId"
                  placeholder="e.g. 543210987..."
                  value={appId}
                  onChange={(e) => setAppId(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="token">Permanent Access Token (System User) *</Label>
              <Input
                id="token"
                type="password"
                placeholder="EAAB..."
                value={accessToken}
                onChange={(e) => setAccessToken(e.target.value)}
                required
              />
              <span className="text-[11px] text-slate-400">
                Generate in Meta Business Manager with permissions: <code>whatsapp_business_messaging</code>, <code>whatsapp_business_management</code>.
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
              <div className="space-y-1.5">
                <Label htmlFor="phone">Phone Number (E.164 format)</Label>
                <Input
                  id="phone"
                  placeholder="+15551234567"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="displayName">Display Name (Optional)</Label>
                <Input
                  id="displayName"
                  placeholder="e.g. WapiFlow Store"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button type="submit" variant="primary" isLoading={connectMutation.isPending}>
                {isConnected ? 'Update Connection' : 'Connect Account'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 3. Webhook Setup Helper */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-primary-600" />
            <div>
              <CardTitle>Meta Webhook Configuration</CardTitle>
              <CardDescription>
                Configure these values in the Meta Developer Portal under WhatsApp &gt; Configuration &gt; Webhook
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Callback URL</Label>
              <div className="flex items-center gap-2 mt-1">
                <Input
                  readOnly
                  value={config?.webhook_url || 'https://api.yourdomain.com/api/v1/webhooks/whatsapp'}
                  className="font-mono text-xs bg-slate-50"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    copyToClipboard(
                      config?.webhook_url || 'https://api.yourdomain.com/api/v1/webhooks/whatsapp',
                      'webhook'
                    )
                  }
                >
                  {copiedField === 'webhook' ? (
                    <Check className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div>
              <Label className="text-xs font-semibold uppercase text-slate-500">Verify Token</Label>
              <div className="flex items-center gap-2 mt-1">
                <Input
                  readOnly
                  value={config?.verify_token || 'wapiflow_verify_token_secure_2026'}
                  className="font-mono text-xs bg-slate-50"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    copyToClipboard(
                      config?.verify_token || 'wapiflow_verify_token_secure_2026',
                      'token'
                    )
                  }
                >
                  {copiedField === 'token' ? (
                    <Check className="h-4 w-4 text-emerald-600" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-600 space-y-1 border border-slate-100">
              <p className="font-semibold text-slate-700">Webhook Subscriptions to enable:</p>
              <p className="font-mono">✓ messages (inbound messages, media, and quick orders)</p>
              <p className="font-mono">✓ message_deliveries (delivery receipts, read receipts)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 4. Test WhatsApp Message */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Send className="h-5 w-5 text-primary-600" />
            <div>
              <CardTitle>Send Test WhatsApp Message</CardTitle>
              <CardDescription>
                Verify that your Meta Cloud API connection can dispatch outbound messages to an active phone number.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSendTest} className="space-y-4">
            {testError && (
              <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                {testError}
              </div>
            )}
            {testResult && (
              <div className="p-3 text-xs bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg">
                <p className="font-semibold">Message Dispatched Successfully!</p>
                <pre className="mt-1 font-mono text-[11px] overflow-x-auto">
                  {JSON.stringify(testResult, null, 2)}
                </pre>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="testPhone">Recipient Phone Number (E.164 format) *</Label>
              <Input
                id="testPhone"
                placeholder="+15551234567"
                value={testPhone}
                onChange={(e) => setTestPhone(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="testText">Test Message Text</Label>
              <Input
                id="testText"
                value={testText}
                onChange={(e) => setTestText(e.target.value)}
                required
              />
            </div>

            <div className="flex justify-end">
              <Button
                type="submit"
                variant="primary"
                disabled={!isConnected}
                isLoading={testMessageMutation.isPending}
              >
                Send Test Message
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
