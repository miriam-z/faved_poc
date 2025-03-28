import styled from 'styled-components'

export const FormContainer = styled.div`
  max-width: 600px;
  margin: 2rem auto;
  padding: 2rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
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
  background-color: #FFB347; /* Faved yellow */
  color: #333; /* Darker text for better contrast on yellow */
  border: none;
  border-radius: 4px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: background-color 0.2s;
  
  &:hover {
    background-color: #FFA726; /* Slightly darker yellow on hover */
  }
  
  &:disabled {
    background-color: #FFE0B2; /* Lighter yellow when disabled */
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

export const EvaluationResults = styled.div`
  margin-top: 2rem;
  padding: 1.5rem;
  border-radius: 8px;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
`

export const ResultsTitle = styled.h3`
  color: #333;
  margin-bottom: 1rem;
  font-size: 1.25rem;
`

export const Decision = styled.div<{ decision: 'ACCEPT' | 'REJECT' }>`
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  font-weight: 600;
  margin-bottom: 1rem;
  background-color: ${props => props.decision === 'ACCEPT' ? '#dcfce7' : '#fee2e2'};
  color: ${props => props.decision === 'ACCEPT' ? '#166534' : '#991b1b'};
`

export const SummarySection = styled.div`
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #eee;
`

export const SummaryTitle = styled.h4`
  color: #666;
  margin-bottom: 0.5rem;
  font-size: 1rem;
`

export const SummaryText = styled.p`
  color: #333;
  line-height: 1.5;
`

export const QuestionList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
`

export const QuestionItem = styled.div`
  padding: 1rem;
  border-radius: 4px;
  background-color: #f8fafc;
`

export const QuestionText = styled.h5`
  color: #333;
  margin-bottom: 0.75rem;
  font-size: 1rem;
`

export const FeedbackItem = styled.div`
  margin-bottom: 0.5rem;
  
  &:last-child {
    margin-bottom: 0;
  }
`

export const FeedbackLabel = styled.span`
  font-weight: 500;
  color: #666;
  margin-right: 0.5rem;
`

export const LoadingOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
`

export const LoadingSpinner = styled.div`
  width: 50px;
  height: 50px;
  border: 3px solid #FFE0B2;
  border-top: 3px solid #FFB347;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`

export const LoadingText = styled.p`
  color: #333;
  font-size: 1.125rem;
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