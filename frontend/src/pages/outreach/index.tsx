import { useState, Suspense } from 'react'
import { AppLayout } from '@/components/AppLayout'
import { Skeleton } from '@/components/ui'
import { CampaignComposer } from '@/components/outreach/CampaignComposer'
import { SequenceBuilder } from '@/components/outreach/SequenceBuilder'
import { FunnelChart } from '@/components/outreach/FunnelChart'

const TAB_LIST = [
  { id: 'campaigns', label: 'Campaigns' },
  { id: 'sequences', label: 'Sequences' },
  { id: 'inbox', label: 'Inbox' },
  { id: 'reports', label: 'Reports' },
]

export default function OutreachPage() {
  const [activeTab, setActiveTab] = useState('campaigns')

  return (
    <AppLayout title="Outreach">
      <div className="flex border-b border-neutral-800 mb-6">
        {TAB_LIST.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-neutral-500 hover:text-neutral-300'
            }`}
            role="tab"
            aria-selected={activeTab === tab.id}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <Suspense fallback={<Skeleton className="h-64 w-full" />}>
        {activeTab === 'campaigns' && <CampaignComposer />}
        {activeTab === 'sequences' && <SequenceBuilder />}
        {activeTab === 'inbox' && (
          <div className="text-neutral-400 text-sm">Inbox — connect reply-handler endpoint</div>
        )}
        {activeTab === 'reports' && <FunnelChart />}
      </Suspense>
    </AppLayout>
  )
}
