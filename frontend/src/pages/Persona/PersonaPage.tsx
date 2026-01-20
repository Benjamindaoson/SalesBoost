import { useQuery } from "@tanstack/react-query";
import { personaService } from "@/services/api";
import { Button } from "@/components/ui/button";
import { Plus, User, Clock, Pencil, Eye, MoreHorizontal } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useNavigate } from "react-router-dom";

export default function PersonaPage() {
  const navigate = useNavigate();
  const { data: personas } = useQuery({
    queryKey: ['personas'],
    queryFn: personaService.getPersonas
  });

  return (
    <div className="space-y-6">
       {/* Header */}
       <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
            <h2 className="text-2xl font-bold text-gray-900">客户预演</h2>
            <p className="text-gray-500">创建个性化客户画像</p>
        </div>
        <Button className="bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-lg">
            <Plus className="mr-2 h-4 w-4" /> 新建预演角色
        </Button>
      </div>

      <div className="space-y-2">
         <h3 className="text-lg font-medium text-gray-900">客户预演</h3>
         <p className="text-sm text-gray-500">选择并创建适合的客户角色进行销售对练。</p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {personas?.map((persona) => (
            <Card key={persona.id} className="overflow-hidden border-none shadow-sm bg-gradient-to-b from-purple-50/50 to-white hover:shadow-md transition-shadow">
                <CardContent className="p-6 flex flex-col items-center text-center h-full relative">
                    {/* Avatar */}
                    <div className="mb-4 p-4 rounded-full bg-white shadow-sm ring-1 ring-purple-100">
                        <User className="h-8 w-8 text-purple-500" />
                    </div>

                    {/* Content */}
                    <h3 className="text-lg font-bold text-gray-900 mb-2">{persona.name}</h3>
                    <p className="text-sm text-gray-500 mb-4 line-clamp-2 min-h-[40px]">
                        {persona.description}
                    </p>

                    {/* Meta */}
                    <div className="w-full flex items-center justify-between text-xs text-gray-400 mb-6">
                         <div className="flex items-center gap-1">
                             <User className="h-3 w-3" /> 
                             <span>张明</span> {/* Hardcoded author based on image */}
                         </div>
                         <div className="flex items-center gap-1">
                             <Clock className="h-3 w-3" />
                             <span>{persona.lastPracticed}</span>
                         </div>
                    </div>

                    {/* Footer Actions */}
                    <div className="mt-auto w-full flex items-center gap-2">
                        <Button
                          className="flex-1 bg-gradient-to-r from-purple-500 to-blue-500 text-white rounded-full"
                          onClick={() =>
                            navigate(`/practice/${persona.id}`, {
                              state: {
                                initialNPCDetails: {
                                  avatar: "/favicon.svg",
                                  tags: persona.tags.slice(0, 3),
                                },
                              },
                            })
                          }
                        >
                          去预演
                        </Button>
                        <Button variant="outline" size="icon" className="h-9 w-9 rounded-full border-gray-200 text-gray-400 hover:text-purple-600">
                            <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="icon" className="h-9 w-9 rounded-full border-gray-200 text-gray-400 hover:text-purple-600">
                            <Eye className="h-4 w-4" />
                        </Button>
                    </div>

                    {persona.note && (
                         <div className="absolute bottom-1 left-0 right-0 text-[10px] text-gray-300 text-center px-2">
                             {persona.note}
                         </div>
                    )}
                </CardContent>
            </Card>
        ))}
      </div>
    </div>
  );
}
