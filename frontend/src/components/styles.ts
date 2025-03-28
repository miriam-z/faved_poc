import styled from 'styled-components'

export const FormContainer = styled.div`
  max-width: 1200px;
  margin: 2rem auto;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  position: relative;
  min-height: 80vh;

  &::after {
    content: '';
    position: absolute;
    top: 2rem;
    bottom: 2rem;
    left: 50%;
    width: 1px;
    background-color: #e2e8f0;
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    &::after {
      display: none;
    }
  }
`

export const LeftColumn = styled.div`
  display: flex;
  flex-direction: column;
  padding-right: 2rem;
`

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  position: relative;
`

export const FormGroup = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`

export const Label = styled.label`
  font-weight: 500;
  color: #333;
`

export const Input = styled.input`
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  
  &:focus {
    outline: none;
    border-color: #0070f3;
    box-shadow: 0 0 0 2px rgba(0, 112, 243, 0.1);
  }
`

export const TextArea = styled.textarea`
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  min-height: 100px;
  resize: vertical;
  
  &:focus {
    outline: none;
    border-color: #0070f3;
    box-shadow: 0 0 0 2px rgba(0, 112, 243, 0.1);
  }
`

export const Button = styled.button`
  padding: 0.75rem 1.5rem;
  background-color: #FFB347;
  color: #333;
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #FFA726;
  }
  
  &:disabled {
    background-color: #FFE0B2;
    cursor: not-allowed;
    color: #666;
  }
`

export const Select = styled.select`
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
  background-color: white;
  
  &:focus {
    outline: none;
    border-color: #0070f3;
    box-shadow: 0 0 0 2px rgba(0, 112, 243, 0.1);
  }
`

export const EvaluationResults = styled.div`
  padding-left: 2rem;
  overflow-y: auto;

  @media (max-width: 768px) {
    padding: 2rem 0 0;
    border-top: 1px solid #e2e8f0;
  }
`

export const ResultsContainer = styled.div`
  margin-top: 2rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`

export const ResultsTitle = styled.h3`
  color: #333;
  margin: 0 0 1rem;
  font-size: 1.25rem;
`

export const Decision = styled.div<{ decision: 'ACCEPT' | 'REJECT' }>`
  display: inline-flex;
  align-items: center;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 600;
  font-size: 0.875rem;
  background-color: ${props => props.decision === 'ACCEPT' ? '#dcfce7' : '#fee2e2'};
  color: ${props => props.decision === 'ACCEPT' ? '#166534' : '#991b1b'};
  width: fit-content;
`

export const SummarySection = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const SummaryTitle = styled.h4`
  color: #333;
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
`

export const SummaryText = styled.p`
  color: #333;
  line-height: 1.5;
  margin: 0;
`

export const QuestionList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 0.5rem 0;
`

export const QuestionItem = styled.div`
  padding: 1.5rem;
  border-radius: 4px;
  background-color: #f8fafc;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
`

export const QuestionText = styled.h5`
  color: #333;
  font-size: 1rem;
  margin: 0;
  font-weight: 600;
`

export const FeedbackItem = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
`

export const FeedbackLabel = styled.span`
  font-weight: 500;
  color: #666;
`

export const LoadingOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.98);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  backdrop-filter: blur(8px);
`

export const LoadingSpinner = styled.div`
  width: 80px;
  height: 80px;
  border: 4px solid #FFE0B2;
  border-top: 4px solid #FFB347;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 2rem;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`

export const LoadingText = styled.p`
  color: #333;
  font-size: 1.5rem;
  margin-top: 1rem;
  background: linear-gradient(
    90deg,
    #FFB347 0%,
    #FFA726 20%,
    #FFB347 40%,
    #FFA726 60%,
    #FFB347 80%,
    #FFA726 100%
  );
  background-size: 200% auto;
  color: transparent;
  background-clip: text;
  -webkit-background-clip: text;
  animation: shimmer 2s linear infinite;
  text-align: center;
  font-weight: 500;
  max-width: 600px;
  padding: 0 2rem;

  @keyframes shimmer {
    to {
      background-position: 200% center;
    }
  }
`

export const ErrorContainer = styled.div`
  padding: 1rem;
  border-radius: 4px;
  background-color: #fee2e2;
  border: 1px solid #fca5a5;
  margin-top: 1rem;
`

export const ErrorTitle = styled.h4`
  color: #991b1b;
  margin-bottom: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
`

export const ErrorDetails = styled.pre`
  color: #7f1d1d;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-break: break-word;
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 2px;
`

export const ErrorMessage = styled.div`
  color: #e00;
  font-size: 0.875rem;
  margin-top: 0.25rem;
`

export const SuccessMessage = styled.div`
  color: #0070f3;
  font-size: 0.875rem;
  margin-top: 0.25rem;
  padding: 0.75rem;
  background-color: rgba(0, 112, 243, 0.1);
  border-radius: 4px;
`