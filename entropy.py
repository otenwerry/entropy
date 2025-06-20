import math
import torch
import sys
from transformers import GPT2LMHeadModel, GPT2TokenizerFast

#downloads and initializes tokenizer for gpt2 model,
#which can split raw text into numerical token ids
tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')

#downloads and loads weights of gpt2 model,
#which can map token id sequences to logits.
#logits are the unnormalized scores for each token
model = GPT2LMHeadModel.from_pretrained('gpt2')
#puts model in evaluation mode, i.e. not training mode
model.eval()

#HELPER FUNCTIONS

@torch.no_grad() #decorator to disable gradient computation to optimize performance
#computesthe probabilities of the next token given the history
def q_prob(token_id: int, history_ids: torch.Tensor) -> float:
    #feeds the history to gpt2 model to get logits
    outputs = model(history_ids)
    logits = outputs.logits #shape (1, T, V)
    #gets the logits for the last token in the sequence
    last_logits = logits[0, -1, :] #shape (V,)
    #softmax(logits) = probabilities. we do log probabilities for numerical reasons.
    log_probs = torch.log_softmax(last_logits, dim=-1)
    #returns the probabilities of the next token,
    #doing exp to cancel the log
    return float(torch.exp(log_probs[token_id]))

#lookup table for background probabilities of each token
bos_id = tokenizer.bos_token_id #beginning of sentence token id
with torch.no_grad():
    #get the logits for the first token after the beginning of sentence token,
    #i.e. the first token in the sentence, and softmax to get probabilities
    out = model(torch.tensor([[bos_id]]))
    logits = out.logits[0, -1, :]
    p_bg_dist = torch.softmax(logits, dim=-1)




#MAIN FUNCTIONS

#computes the bits of information content in a string of english text
def info_content(text: str):
    #tokenizes text string into token ids
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids[0] #Shape (N,)
    #iterate through the tokens and add the entropy of each,
    #starting at 1 because the first token has no history
    total_bits = 0.0
    for i in range(1,len(ids)):
        #takes the first i tokens and adds a dimension
        history_ids = ids[:i].unsqueeze(0) #Shape (1,i)
        #gets the probability of the next token
        p_next = q_prob(int(ids[i]), history_ids)
        #if probability is 0, the log is -inf, which is bad; and probabilities can't be < 0.
        #softmax returns nonzero probabilities anyway.
        if p_next <= 0:
            raise ValueError(f"Invalid probability: {tokenizer.decode(ids[i])}")
        #add bits of this next token: I(x) = -log_2(p(x))
        total_bits += -math.log2(p_next)
    #returns total bits and bits per token
    #we subtract 1 for the average because we didn't compute bits of first token
    return total_bits, total_bits/(len(ids) - 1)

#computes the bits of information content in a string of english text,
#corrected for the background probability of each token
#(aka negative PMI?)
def info_content_background_corrected(text: str):
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids[0]
    total_bits = 0.0
    for i in range(1,len(ids)):
        history_ids = ids[:i].unsqueeze(0)
        p_next = q_prob(int(ids[i]), history_ids)
        p_background = float(p_bg_dist[int(ids[i])])
        if p_next <= 0:
            raise ValueError(f"Invalid probability: {tokenizer.decode(ids[i])}")
        total_bits += -math.log2(p_next) + math.log2(p_background)
    return total_bits, total_bits/(len(ids) - 1)




if __name__ == "__main__":
    #if you want line breaks, you need to format it this way 
    # rather than with triple quotes, for token reasons
    
    sample = ( 
        "Machines are embedded in art so deeply that we don’t even really notice them. Most writers don’t think it’s a perversion of their work to type it on a computer. Even the most conservative likely doesn’t deactivate the spell check built into Google Docs or Microsoft Word. But that same writer probably rebukes ChatGPT and regards AI-produced writing as second class, in hypotheticals and when they can spot it. They complain with their friends and at conferences about how it makes bad content and defiles the craft and yet is slowly but surely displacing creators in their industry. Fundamentally, a lot of artists don’t regard AI-generated art as art. Some instances of engineering in art are acceptable, though; they might defend the honor of an artist who uses a tool like Procreate to create animations and drawings. They admire the daring of a readymade sculpture."
    )

    '''if len(sys.argv) > 1:
        # If text is passed as command line argument
        sample = sys.argv[1]
    else:
        # Read from stdin
        sample = sys.stdin.read().strip()
    
    if not sample:
        print("Error: No text provided")
        sys.exit(1)'''
    sample = sys.stdin.read().strip()
    total_bits, per_token_bits = info_content(sample)
    print(sample)
    print(f"Character count: {len(sample)}")
    print(f"Total tokens: {total_bits / per_token_bits}")
    print(f"Total bits: {total_bits:.2f}")
    print(f"Bits per token: {per_token_bits:.2f}")
    print(f"Background corrected total bits: {info_content_background_corrected(sample)[0]:.2f}")
    print(f"Background corrected bits per token: {info_content_background_corrected(sample)[1]:.2f}")