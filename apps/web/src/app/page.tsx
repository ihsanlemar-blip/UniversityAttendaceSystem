import React from 'react';

export default function HomePage() {
  return (
    <main style={{ padding: '3rem', maxWidth: '800px', margin: '0 auto', textAlign: 'center' }}>
      <h1>Digital Student Attendance System</h1>
      <p style={{ color: '#666', fontSize: '1.2rem', marginTop: '1rem' }}>
        University Academic Attendance & Session Governance Portal
      </p>
      <div style={{
        marginTop: '2rem',
        padding: '1.5rem',
        backgroundColor: '#f4f4f5',
        borderRadius: '8px',
        border: '1px solid #e4e4e7',
        textAlign: 'left'
      }}>
        <h3 style={{ margin: '0 0 0.5rem 0' }}>Repository Status: Milestone 3 Baseline</h3>
        <p style={{ margin: '0', color: '#52525b', fontSize: '0.95rem' }}>
          Monorepo bootstrap and architectural blueprint established. Feature implementation commences in Milestone 4.
        </p>
      </div>
    </main>
  );
}
