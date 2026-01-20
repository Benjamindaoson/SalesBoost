import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export function NPCMessageItem(props: { avatar: string; content: string }) {
  return (
    <div className="flex items-end gap-3 px-4 py-3" data-testid="chat-message">
      <Avatar className="h-8 w-8 ring-1 ring-gray-200">
        <AvatarImage src={props.avatar} alt="NPC" />
        <AvatarFallback className="bg-gray-100 text-gray-600">NPC</AvatarFallback>
      </Avatar>
      <div className="max-w-[75%] rounded-2xl rounded-bl-md bg-gray-100 px-4 py-2.5 text-sm text-gray-800">
        {props.content}
      </div>
    </div>
  );
}

