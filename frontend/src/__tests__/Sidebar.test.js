import React from 'react';
import { render, screen } from '@testing-library/react';
import Sidebar from '@/components/Sidebar';

// Mock props for the Sidebar component
const mockProps = {
  providers: [{ name: 'ollama' }, { name: 'gemini' }],
  models: ['llama3', 'gemini-pro'],
  sessions: [{ name: 'Session_1' }, { name: 'Session_2' }],
  currentSessionName: 'Session_1',
  onProviderChange: jest.fn(),
  onModelChange: jest.fn(),
  onSessionClick: jest.fn(),
  onOpenSettings: jest.fn(),
  selectedProvider: 'ollama',
  selectedModel: 'llama3',
};

describe('Sidebar Component', () => {
  it('renders without crashing and displays the title', () => {
    render(<Sidebar {...mockProps} />);
    
    // Check if the main title is visible
    const titleElement = screen.getByText(/🚀 CROT/i);
    expect(titleElement).toBeInTheDocument();
  });

  it('displays the correct number of providers and sessions', () => {
    render(<Sidebar {...mockProps} />);

    // Check if provider options are rendered
    const providerOptions = screen.getAllByRole('option');
    // Note: This is a simple check; a more robust test would check values
    expect(providerOptions.length).toBe(mockProps.providers.length + mockProps.models.length);

    // Check if session items are rendered
    const sessionItems = screen.getAllByText(/Session_/i);
    expect(sessionItems.length).toBe(mockProps.sessions.length);
  });
});
