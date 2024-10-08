from abc import ABC
from typing import Any, List, Mapping, Optional, Dict
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, AutoModelForCausalLM


def get_messages(request: Mapping[str, Any]) -> List[Dict[str,str]]:
    messages = request['messages']
    return messages


def _completions_auto(
        request: Mapping[str, Any],
        tokenizer: Any,
        tokenizer_device: Optional[str],
        model: Any,
        generate_config: Mapping[str, Any],
        decode_config: Mapping[str, Any],
        auto_echo: bool):
    generate_args = {}
    generate_args.update(generate_config)
    #generate_args.update(request)

    decode_args = {
        "skip_special_tokens": True
    }
    decode_args.update(decode_config)

    if ('top_p' in generate_args or 'top_k' in generate_args or 'temperature' in generate_args) and 'do_sample' not in generate_args:
        generate_args['do_sample'] = True
        if generate_args.get('temperature', 1.0) == 0:
            generate_args.pop('temperature', None)
        elif generate_args.get('top_p', 1.0) == 1.0:
            generate_args.pop('top_p', None)
        if 'top_k' not in generate_args:
            generate_args['top_k'] = 0

    messages = get_messages(request)
    echo = generate_args.get('echo', False)
    n = generate_args.get('n', 1)

    generate_args.pop('model', None)
    generate_args.pop('prompt', None)
    generate_args.pop('n', None)

    # TODO
    generate_args.pop('best_of', None)
    generate_args.pop('presence_penalty', None)
    generate_args.pop('frequency_penalty', None)
    generate_args.pop('logit_bias', None)

    inputs = []
    prompt_tokens_count = 0
    input = tokenizer.apply_chat_template(messages, tokenize=True, return_tensors="pt", add_generation_prompt=True)
    if tokenizer_device is not None:
        input = input.to(tokenizer_device)
    inputs.append(input)
    prompt_tokens_count += input.size(dim=1)

    choices = []
    completion_tokens_count = 0
    for i in range(0, len(inputs)):
        for _ in range(0, n):
            output = model.generate(inputs[i], **generate_args)[0]
            completion_tokens_count += len(output)
            text = tokenizer.decode(output, **decode_args)
            if echo and not auto_echo:
                text = inputs[i] + text
            choices.append({
                'message': {"role": "assistant", "content": text},
                "index": i
            })

    return {
        'choices': choices,
        'usage': {
            'prompt_tokens': prompt_tokens_count,
            'completion_tokens': completion_tokens_count,
            'total_tokens': prompt_tokens_count + completion_tokens_count
        }
    }


class Model(ABC):

    def completions(self, request: Mapping[str, Any]):
        pass


class Seq2Seq(Model):
    model: AutoModelForSeq2SeqLM
    tokenizer: AutoTokenizer
    generate_config: Mapping[str, Any]
    decode_config: Mapping[str, Any]
    tokenizer_device: Optional[str]

    def __init__(
            self,
            pretrained_model_name_or_path: str,
            model_config: Mapping[str, Any],
            model_device: Optional[str],
            tokenizer_config: Mapping[str, Any],
            tokenizer_device: Optional[str],
            generate_config: Mapping[str, Any],
            decode_config: Mapping[str, Any]) -> None:
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            pretrained_model_name_or_path, **model_config)
        if model_device is not None:
            self.model = self.model.to(model_device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path, **tokenizer_config)
        self.generate_config = generate_config
        self.decode_config = decode_config
        self.tokenizer_device = tokenizer_device

    def completions(self, request) -> List[str]:
        return _completions_auto(request, self.tokenizer, self.tokenizer_device, self.model, self.generate_config, self.decode_config, False)


class CausalLM(Model):
    model: AutoModelForCausalLM
    tokenizer: AutoTokenizer
    generate_config: Mapping[str, Any]
    decode_config: Mapping[str, Any]
    tokenizer_device: Optional[str]

    def __init__(
            self,
            pretrained_model_name_or_path: str,
            model_config: Mapping[str, Any],
            model_device: Optional[str],
            tokenizer_config: Mapping[str, Any],
            tokenizer_device: Optional[str],
            generate_config: Mapping[str, Any],
            decode_config: Mapping[str, Any]) -> None:
        self.model = AutoModelForCausalLM.from_pretrained(
            pretrained_model_name_or_path, **model_config)
        if model_device is not None:
            self.model = self.model.to(model_device)
        self.tokenizer = AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path, **tokenizer_config)
        self.generate_config = generate_config
        self.decode_config = decode_config
        self.tokenizer_device = tokenizer_device

    def completions(self, request) -> List[str]:
        return _completions_auto(request, self.tokenizer, self.tokenizer_device, self.model, self.generate_config, self.decode_config, False)
